from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from app.services.trick_store import (
    get_pending,
    get_approved,
    approve_pending
)

router = APIRouter(prefix="/admin", tags=["Admin"])

ALLOWED_UPLOADS = {
    "billable_time.csv": {"type": "raw", "target": "billable_time.csv"},
    "tech_notes.csv": {"type": "raw", "target": "tech_notes.csv"},
    "customers.csv": {"type": "customers_csv", "target": "customers_db.json"},
    "contacts.csv": {"type": "contacts_csv", "target": "contacts_db.json"},
}


def _require_admin(request: Request) -> None:
    role = getattr(request.state, "auth_role", None)
    if role != "office_admin":
        raise HTTPException(status_code=403, detail="Office admin access required")


def _data_dir(request: Request) -> Path:
    base = getattr(request.app.state, "data_dir", None)
    if base:
        return Path(base)
    return Path(__file__).resolve().parents[2] / "data"


def _normalize_key(value: str) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _pick(row: dict, *names: str) -> str:
    normalized = {_normalize_key(k): v for k, v in (row or {}).items()}
    for name in names:
        val = normalized.get(_normalize_key(name))
        if val is not None and str(val).strip() != "":
            return str(val).strip()
    return ""


def _convert_customers_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    items: list[dict] = []
    seen = set()
    for idx, row in enumerate(reader, start=1):
        company_name = _pick(row, "company_name", "customer", "customer_name", "name", "company", "business_name")
        if not company_name:
            continue
        address = _pick(row, "address", "street_address", "street", "job_address", "service_address")
        city = _pick(row, "city")
        state = _pick(row, "state")
        zip_code = _pick(row, "zip", "zip_code", "zipcode", "postal_code")
        phone_number = _pick(row, "phone", "phone_number", "office_phone", "business_phone")
        email = _pick(row, "email", "email_address")
        notes = _pick(row, "notes", "note", "customer_notes")

        item = {
            "id": f"cust_{idx}",
            "company_name": company_name,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "phone_number": phone_number,
            "email": email,
            "notes": notes,
        }
        key = (company_name.lower(), address.lower(), city.lower(), state.lower(), zip_code.lower())
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def _convert_contacts_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    items: list[dict] = []
    seen = set()
    for idx, row in enumerate(reader, start=1):
        name = _pick(row, "name", "contact_name", "full_name", "contact")
        if not name:
            first = _pick(row, "first_name", "firstname")
            last = _pick(row, "last_name", "lastname")
            name = " ".join([x for x in [first, last] if x]).strip()
        if not name:
            continue

        company_name = _pick(row, "company_name", "customer", "customer_name", "company")
        phone_number = _pick(row, "phone", "phone_number", "office_phone", "work_phone")
        cell_phone = _pick(row, "cell", "cell_phone", "mobile", "mobile_phone")
        email = _pick(row, "email", "email_address")
        title = _pick(row, "title", "job_title", "role")
        notes = _pick(row, "notes", "note", "contact_notes")

        item = {
            "id": f"cont_{idx}",
            "name": name,
            "company_name": company_name,
            "phone_number": phone_number,
            "cell_phone": cell_phone,
            "email": email,
            "title": title,
            "notes": notes,
        }
        key = (name.lower(), company_name.lower(), email.lower(), phone_number.lower(), cell_phone.lower())
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


@router.get("/pending")
def get_pending_tricks():
    pending = get_pending()
    return {"count": len(pending), "pending": pending}


@router.get("/approved")
def get_approved_tricks():
    approved = get_approved()
    return {"count": len(approved), "approved": approved}


@router.post("/approve")
def approve_pending_trick(pending_id: str):
    result = approve_pending(pending_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Pending trick not found")
    return result


@router.post("/upload-data-file")
async def upload_data_file(request: Request, file: UploadFile = File(...)):
    _require_admin(request)

    filename = str(file.filename or "").strip()
    cfg = ALLOWED_UPLOADS.get(filename)
    if not cfg:
        raise HTTPException(status_code=400, detail="Allowed files: billable_time.csv, tech_notes.csv, customers.csv, contacts.csv")

    data_dir = _data_dir(request)
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / cfg["target"]
    tmp_target = target.with_suffix(target.suffix + ".tmp")

    try:
        file_bytes = await file.read()
        if cfg["type"] == "raw":
            with tmp_target.open("wb") as fh:
                fh.write(file_bytes)
        elif cfg["type"] == "customers_csv":
            items = _convert_customers_csv(file_bytes)
            with tmp_target.open("w", encoding="utf-8") as fh:
                json.dump({"items": items}, fh, indent=2, ensure_ascii=False)
        elif cfg["type"] == "contacts_csv":
            items = _convert_contacts_csv(file_bytes)
            with tmp_target.open("w", encoding="utf-8") as fh:
                json.dump({"items": items}, fh, indent=2, ensure_ascii=False)
        else:
            raise HTTPException(status_code=500, detail="Unsupported upload config")
        tmp_target.replace(target)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    return {"ok": True, "filename": filename, "saved_to": str(target)}
