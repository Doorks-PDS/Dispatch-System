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

@router.post('/extract')
async def extract_receipt(request: Request, file: UploadFile = File(...), x_api_key: Optional[str] = Header(default=None)):
    """Best-effort OCR. Does not store the uploaded image or change saved receipts."""
    _require(request, x_api_key)
    import io
    import shutil
    import subprocess
    import tempfile
    from datetime import datetime
    from pypdf import PdfReader
    from PIL import Image, ImageOps

    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, 'Upload a JPG, PNG, WEBP, HEIC, or PDF')
    raw = await file.read(MAX_SIZE + 1)
    if not raw or len(raw) > MAX_SIZE:
        raise HTTPException(400, 'Receipt must be between 1 byte and 12 MB')
    text = ''
    if suffix == '.pdf':
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages[:3])
        except Exception:
            pass
    if not text.strip() and suffix != '.pdf':
        if not shutil.which('tesseract'):
            return {'ok': True, 'fields': {}, 'message': 'Image reading is not enabled on this server (Tesseract OCR is unavailable).'}
        try:
            image = Image.open(io.BytesIO(raw))
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((2400, 2400))
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'receipt.png'
                image.save(path)
                proc = subprocess.run(['tesseract', str(path), 'stdout'], capture_output=True, text=True, timeout=15)
                if proc.returncode == 0:
                    text = proc.stdout
        except Exception:
            pass
    if not text.strip():
        return {'ok': True, 'fields': {}, 'message': 'No readable text found. Scanned PDFs require OCR; please enter details manually.'}

    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    fields = {}
    for line in lines[:8]:
        if not re.search(r'(?i)receipt|invoice|transaction|date|total|subtotal|tax|visa|mastercard|amex|change|cash|www\.|http', line) and len(line) >= 3 and re.search('[A-Za-z]', line):
            fields['vendor'] = line[:100]
            break
    date_patterns = [r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', r'\b(20\d{2})-(\d{1,2})-(\d{1,2})\b']
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                a, b, c = [int(x) for x in match.groups()]
                if pattern == date_patterns[0]:
                    year = c + 2000 if c < 100 else c
                    parsed = datetime(year, a, b)
                else:
                    parsed = datetime(a, b, c)
                fields['date'] = parsed.strftime('%Y-%m-%d')
                break
            except ValueError:
                pass
    for line in lines:
        match = re.search(r'(?i)\b(?:grand\s+total|amount\s+paid|total\s+due|total)\b\s*[:$ ]*\$?\s*(\d{1,6}[.,]\d{2})\b', line)
        if match and not re.search(r'(?i)subtotal|tax\s+total', line):
            fields['amount'] = match.group(1).replace(',', '.')
    for line in lines:
        match = re.search(r'(?i)\b(?:receipt|invoice|transaction)\s*(?:number|no\.?|#|id)\s*[:# ]+([A-Z0-9-]{3,35})', line)
        if match:
            fields['receipt_number'] = match.group(1)
            break
    return {'ok': True, 'fields': fields, 'message': 'Read available text; review all extracted values.'}
