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
        company_name = _pick(
            row,
            "Company Name", "company_name", "customer", "customer_name", "name", "company", "business_name"
        )
        if not company_name:
            continue
        address = _pick(row, "Address", "address", "street_address", "street", "job_address", "service_address")
        city = _pick(row, "City", "city")
        state = _pick(row, "State", "state")
        zip_code = _pick(row, "ZIP", "Zip", "zip", "zip_code", "zipcode", "postal_code")
        phone_number = _pick(row, "Phone Number", "phone", "phone_number", "office_phone", "business_phone")
        email = _pick(row, "Email", "email", "email_address")
        notes = _pick(row, "Notes", "notes", "note", "customer_notes")

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


def _convert_contacts_csv(file_bytes: bytes, data_dir: Path) -> list[dict]:
    customers_path = data_dir / "customers_db.json"
    customer_rows = []
    try:
        raw = json.loads(customers_path.read_text(encoding="utf-8")) if customers_path.exists() else {"items": []}
        customer_rows = raw.get("items", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    except Exception:
        customer_rows = []

    customer_map = {
        _normalize_key(str(c.get("company_name") or "")): str(c.get("id") or "")
        for c in customer_rows if isinstance(c, dict)
    }

    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    items: list[dict] = []
    seen = set()
    for idx, row in enumerate(reader, start=1):
        name = _pick(row, "Name", "name", "contact_name", "full_name", "contact", "Contact Name")
        if not name:
            first = _pick(row, "First Name", "first_name", "firstname")
            last = _pick(row, "Last Name", "last_name", "lastname")
            name = " ".join([x for x in [first, last] if x]).strip()
        if not name:
            continue

        company_name = _pick(
            row,
            "Customer - Company Name", "customer_company_name", "company_name",
            "customer", "customer_name", "company", "Company Name"
        )
        phone_number = _pick(row, "Phone Number", "phone", "phone_number", "office_phone", "work_phone")
        cell_phone = _pick(row, "Cell Phone", "cell", "cell_phone", "mobile", "mobile_phone")
        email = _pick(row, "Email", "email", "email_address")
        title = _pick(row, "Title", "title", "job_title", "role")
        notes = _pick(row, "Notes", "notes", "note", "contact_notes")
        customer_id = customer_map.get(_normalize_key(company_name), "")

        item = {
            "id": f"cont_{idx}",
            "name": name,
            "company_name": company_name,
            "customer_id": customer_id,
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
            items = _convert_contacts_csv(file_bytes, data_dir)
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
