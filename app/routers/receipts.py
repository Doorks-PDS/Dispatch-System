"""Standalone receipts, stored on the existing persistent Doorks data disk."""
from __future__ import annotations

import json
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

router = APIRouter(prefix="/receipts", tags=["receipts"])
_lock = Lock()
MAX_SIZE = 12 * 1024 * 1024
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".pdf"}


def _require(request: Request, key: Optional[str]):
    if not getattr(request.state, "auth_user", None):
        request.app.state.require_key(key)


def _paths(request: Request):
    base = Path(request.app.state.data_dir) / "receipts"
    base.mkdir(parents=True, exist_ok=True)
    return base, base / "receipts.json"


def _load(path: Path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


@router.get("")
def list_receipts(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    _, index = _paths(request)
    items = _load(index)
    role = str(getattr(request.state, "auth_role", "") or "")
    user = getattr(request.state, "auth_user", None) or {}
    if role in {"tech", "lead"}:
        own = str(user.get("name") or user.get("username") or "").strip().casefold()
        items = [i for i in items if str(i.get("employee", "")).strip().casefold() == own]
    return {"ok": True, "items": list(reversed(items))}


@router.post("")
async def create_receipt(
    request: Request,
    date: str = Form(...), employee: str = Form(...), vendor: str = Form(...),
    amount: float = Form(...), card_last4: str = Form(""), receipt_number: str = Form(""),
    notes: str = Form(""), file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
):
    _require(request, x_api_key)
    if not date.strip() or not vendor.strip() or not employee.strip() or amount < 0:
        raise HTTPException(400, "Date, employee, vendor and nonnegative amount are required")
    if card_last4 and not re.fullmatch(r"\d{4}", card_last4):
        raise HTTPException(400, "Enter only the last four digits of the card")
    role = str(getattr(request.state, "auth_role", "") or "")
    user = getattr(request.state, "auth_user", None) or {}
    if role in {"tech", "lead"}:
        employee = str(user.get("name") or user.get("username") or "")
    original = Path(file.filename or "receipt").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, "Upload a JPG, PNG, WEBP, HEIC, or PDF")
    data = await file.read(MAX_SIZE + 1)
    if not data or len(data) > MAX_SIZE:
        raise HTTPException(400, "Receipt must be between 1 byte and 12 MB")
    base, index = _paths(request)
    item_id = uuid.uuid4().hex
    filename = item_id + suffix
    record = {
        "id": item_id, "date": date.strip(), "employee": employee.strip(),
        "vendor": vendor.strip(), "amount": round(amount, 2),
        "card_last4": card_last4, "receipt_number": receipt_number.strip()[:120],
        "notes": notes.strip()[:2000], "filename": original,
        "stored_file": filename, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        target = base / filename
        target.write_bytes(data)
        try:
            items = _load(index)
            items.append(record)
            tmp = index.with_suffix(".tmp")
            tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
            tmp.replace(index)
        except Exception:
            target.unlink(missing_ok=True)
            raise
    return {"ok": True, "item": record}


@router.get("/{receipt_id}/file")
def get_receipt_file(request: Request, receipt_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    base, index = _paths(request)
    item = next((r for r in _load(index) if r.get("id") == receipt_id), None)
    if not item:
        raise HTTPException(404, "Receipt not found")
    role = str(getattr(request.state, "auth_role", "") or "")
    user = getattr(request.state, "auth_user", None) or {}
    if role in {"tech", "lead"}:
        own = str(user.get("name") or user.get("username") or "").strip().casefold()
        if str(item.get("employee", "")).strip().casefold() != own:
            raise HTTPException(403, "Receipt belongs to another employee")
    target = base / Path(item["stored_file"]).name
    if not target.is_file():
        raise HTTPException(404, "Receipt file missing")
    return FileResponse(target, media_type=mimetypes.guess_type(str(target))[0] or "application/octet-stream", filename=item["filename"])
