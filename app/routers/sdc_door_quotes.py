"""Public Saddleback custom-door requests; private, durable SDC review queue.

No PDS reads/writes, email sending, payment collection, or automatic marketing.
All data and attachments are written below the configured writable data directory.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.routers import workspaces as ws

router = APIRouter(tags=["sdc-door-quotes"])

MAX_PHOTOS = 5
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 43 * 1024 * 1024
STYLES = {"Single", "Double", "Bi-fold", "Sliding", "Barn", "Other"}
FULFILLMENT = {"Shipping", "Local pickup", "Not sure"}
STATUSES = {"New", "Reviewing", "Quoted", "Closed"}


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _base(request: Request) -> Path:
    # Data directory is supplied by the existing storage system, not the source tree.
    return Path(request.app.state.data_dir) / "business_workspaces" / "sdc"


def _records_path(request: Request) -> Path:
    return _base(request) / "door_quote_requests.json"


def _photos_path(request: Request, request_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise HTTPException(404, "Request not found")
    return _base(request) / "door_quote_photos" / request_id


def _staff(request: Request) -> None:
    ws.guard(request, "sdc", "software_leads")


def _email_ok(value: str) -> bool:
    value = value.strip()
    return bool(re.fullmatch(r"[^\s@]{1,100}@[^\s@.]{1,125}(?:\.[^\s@.]{2,30})+", value))


def _file_type(header: bytes) -> tuple[str, str] | None:
    if header.startswith(b"\xff\xd8\xff"):
        return ("jpg", "image/jpeg")
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("png", "image/png")
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ("webp", "image/webp")
    # HEIC/HEIF photos from some phones; stored as attachments, not executed.
    if len(header) >= 12 and header[4:8] == b"ftyp" and header[8:12] in {
        b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"
    }:
        return ("heic", "image/heic")
    return None


def _created(row: dict) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(row.get("created_at", "")).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def _matching(rows: list, *, email: str, style: str, width: str, height: str, now: datetime):
    for row in reversed(rows):
        if (not isinstance(row, dict) or str(row.get("email", "")).casefold() != email.casefold()
                or row.get("door_style") != style or row.get("opening_width") != width
                or row.get("opening_height") != height):
            continue
        when = _created(row)
        if when and now - timedelta(minutes=2) <= when <= now:
            return row
    return None


def _read_existing(path: Path) -> list:
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "Quote request storage unavailable") from exc
    if not isinstance(rows, list):
        raise HTTPException(500, "Quote request storage unavailable")
    return rows


def _save(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with staging.open("w", encoding="utf-8") as output:
            json.dump(rows, output, indent=2, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


@router.get("/saddleback/doors")
def custom_door_landing(request: Request):
    root = Path(request.app.state.project_root)
    return FileResponse(root / "static" / "sdc_doors.html", media_type="text/html",
                        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})


@router.post("/api/saddleback/door-quotes", status_code=201)
async def submit_door_quote(
    request: Request,
    full_name: str = Form(..., min_length=1, max_length=120),
    email: str = Form(..., min_length=3, max_length=254),
    phone: str = Form("", max_length=45),
    door_style: str = Form(..., max_length=30),
    door_count: int = Form(..., ge=1, le=20),
    opening_width: str = Form(..., max_length=30),
    opening_height: str = Form(..., max_length=30),
    measurement_unit: str = Form("in", max_length=10),
    wood_finish: str = Form("", max_length=180),
    material: str = Form("", max_length=80),
    notes: str = Form("", max_length=2500),
    fulfillment: str = Form(..., max_length=30),
    postal_code: str = Form("", max_length=30),
    timeline: str = Form("", max_length=120),
    website: str = Form("", max_length=160),  # honeypot
    utm_source: str = Form("", max_length=100),
    utm_medium: str = Form("", max_length=100),
    utm_campaign: str = Form("", max_length=100),
    photos: list[UploadFile] | None = File(None),
):
    if website.strip():
        return {"ok": True, "message": "Request received"}
    try:
        request_bytes = int(request.headers.get("content-length", "0") or "0")
    except ValueError:
        raise HTTPException(400, "Invalid request size")
    if request_bytes > MAX_REQUEST_BYTES:
        raise HTTPException(413, "Request is too large")
    full_name, email = full_name.strip(), email.strip().lower()
    width, height = opening_width.strip(), opening_height.strip()
    if not _email_ok(email):
        raise HTTPException(422, "Enter a valid email address")
    if not full_name or len(full_name) > 120:
        raise HTTPException(422, "Enter your name")
    if door_style not in STYLES or fulfillment not in FULFILLMENT or measurement_unit not in {"in", "cm"}:
        raise HTTPException(422, "Select valid door and delivery options")
    if not all(re.fullmatch(r"\d{1,4}(?:\.\d{1,2})?", s) and 0 < float(s) <= 1000 for s in (width, height)):
        raise HTTPException(422, "Enter valid positive opening dimensions")
    if fulfillment == "Shipping" and not postal_code.strip():
        raise HTTPException(422, "Enter the shipping ZIP or postal code")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in notes + full_name + wood_finish):
        raise HTTPException(422, "Invalid text")
    pictures = [f for f in photos or [] if f.filename]
    if len(pictures) > MAX_PHOTOS:
        raise HTTPException(413, "Maximum five reference photos")

    # Read uploads BEFORE acquiring the synchronous workspace lock. Async awaits
    # inside a threading.RLock would permit same-thread coroutine interleaving.
    now = _utc()
    request_id = uuid.uuid4().hex
    photo_dir = _photos_path(request, request_id)
    saved: list[dict] = []
    try:
        for photo in pictures:
            # Validate actual file signature, not the filename or MIME claim.
            first = await photo.read(32)
            detected = _file_type(first)
            if detected is None:
                raise HTTPException(422, "Photos must be JPG, PNG, WebP or HEIC")
            suffix, mime = detected
            photo_dir.mkdir(parents=True, exist_ok=True)
            file_name = uuid.uuid4().hex + "." + suffix
            count = len(first)
            with (photo_dir / file_name).open("xb") as dest:
                dest.write(first)
                while chunk := await photo.read(64 * 1024):
                    count += len(chunk)
                    if count > MAX_FILE_BYTES:
                        raise HTTPException(413, "Each photo must be 8 MB or less")
                    dest.write(chunk)
            saved.append({"file": file_name, "mime": mime, "bytes": count})
        with ws._lock:  # same write coordination model as the existing SDC workspace
            path = _records_path(request)
            rows = _read_existing(path)
            previous = _matching(rows, email=email, style=door_style, width=width, height=height, now=now)
            if previous:
                shutil.rmtree(photo_dir, ignore_errors=True)
                return {"ok": True, "message": "Request received", "reference": str(previous["id"])[:8], "duplicate": True}
            attempts = sum(1 for row in rows if isinstance(row, dict)
                           and str(row.get("email", "")).casefold() == email
                           and (when := _created(row)) and now - timedelta(hours=1) <= when <= now)
            if attempts >= 5:
                raise HTTPException(429, "Too many requests. Please try again later")
            record = {
                "id": request_id, "created_at": now.isoformat(), "status": "New",
                "full_name": full_name, "email": email, "phone": phone.strip(),
                "door_style": door_style, "door_count": door_count,
                "opening_width": width, "opening_height": height,
                "measurement_unit": measurement_unit, "wood_finish": wood_finish.strip(),
                "material": material.strip(), "notes": notes.strip(),
                "fulfillment": fulfillment, "postal_code": postal_code.strip(),
                "timeline": timeline.strip(), "photos": saved,
                "utm_source": utm_source.strip(), "utm_medium": utm_medium.strip(),
                "utm_campaign": utm_campaign.strip(), "source": "sdc_public_custom_door_form",
                "staff_notes": "", "updated_at": now.isoformat(),
            }
            rows.append(record)
            _save(path, rows)
    except BaseException:
        shutil.rmtree(photo_dir, ignore_errors=True)
        raise
    return {"ok": True, "message": "Request received", "reference": request_id[:8]}


@router.get("/sdc/door-quote-requests")
def door_quote_staff_page(request: Request):
    _staff(request)
    return FileResponse(Path(request.app.state.project_root) / "static" / "sdc_door_quote_requests.html",
                        media_type="text/html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


@router.get("/api/saddleback/door-quotes")
def list_door_quotes(request: Request):
    _staff(request)
    with ws._lock:
        rows = _read_existing(_records_path(request))
    return {"items": sorted(rows, key=lambda row: str(row.get("created_at", "")), reverse=True)}


class DoorQuoteUpdate(BaseModel):
    status: Literal["New", "Reviewing", "Quoted", "Closed"]
    staff_notes: str = Field(default="", max_length=2500)


@router.patch("/api/saddleback/door-quotes/{request_id}")
def update_door_quote(request_id: str, payload: DoorQuoteUpdate, request: Request):
    _staff(request)
    with ws._lock:
        path = _records_path(request)
        rows = _read_existing(path)
        row = next((x for x in rows if isinstance(x, dict) and x.get("id") == request_id), None)
        if row is None:
            raise HTTPException(404, "Quote request not found")
        row.update(status=payload.status, staff_notes=payload.staff_notes.strip(), updated_at=_utc().isoformat())
        user = getattr(request.state, "auth_user", None)
        row["updated_by"] = str(user.get("id") or user.get("username") or "office_admin")[:80] if isinstance(user, dict) else "office_admin"
        _save(path, rows)
        return {"ok": True, "item": row}


@router.get("/api/saddleback/door-quotes/{request_id}/photos/{index}")
def get_door_quote_photo(request_id: str, index: int, request: Request):
    _staff(request)
    with ws._lock:
        rows = _read_existing(_records_path(request))
        row = next((x for x in rows if isinstance(x, dict) and x.get("id") == request_id), None)
    if row is None or index < 0 or index >= len(row.get("photos", [])):
        raise HTTPException(404, "Photo not found")
    photo = row["photos"][index]
    filename = str(photo.get("file", ""))
    if not re.fullmatch(r"[0-9a-f]{32}\.(?:jpg|png|webp|heic)", filename):
        raise HTTPException(404, "Photo not found")
    path = _photos_path(request, request_id) / filename
    if not path.is_file():
        raise HTTPException(404, "Photo not found")
    return FileResponse(path, media_type=photo.get("mime", "application/octet-stream"),
                        filename=f"door-reference-{index+1}.{path.suffix.lstrip('.')}",
                        content_disposition_type="inline",
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                                 "X-Robots-Tag": "noindex, nofollow"})
