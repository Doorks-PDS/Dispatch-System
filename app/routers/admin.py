from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from app.services.trick_store import (
    load_pending,
    load_approved,
    approve_trick
)

router = APIRouter(prefix="/admin", tags=["Admin"])

ALLOWED_UPLOADS = {
    "billable_time.csv": "billable_time.csv",
    "tech_notes.csv": "tech_notes.csv",
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


@router.get("/pending")
def get_pending_tricks():
    return {
        "count": len(load_pending()),
        "pending": load_pending()
    }


@router.get("/approved")
def get_approved_tricks():
    return {
        "count": len(load_approved()),
        "approved": load_approved()
    }


@router.post("/approve")
def approve_pending_trick(query: str):
    pending = load_pending()
    if not any(t.get("query") == query for t in pending):
        raise HTTPException(status_code=404, detail="Pending trick not found")

    approve_trick(query)

    return {
        "status": "approved",
        "query": query
    }


@router.post("/upload-data-file")
async def upload_data_file(request: Request, file: UploadFile = File(...)):
    _require_admin(request)

    filename = str(file.filename or "").strip()
    if filename not in ALLOWED_UPLOADS:
        raise HTTPException(status_code=400, detail="Only billable_time.csv and tech_notes.csv are allowed.")

    data_dir = _data_dir(request)
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / ALLOWED_UPLOADS[filename]
    tmp_target = target.with_suffix(target.suffix + ".tmp")

    try:
        with tmp_target.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
        tmp_target.replace(target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    return {"ok": True, "filename": filename, "saved_to": str(target)}
