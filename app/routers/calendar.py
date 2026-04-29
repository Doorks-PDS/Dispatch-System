from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _store(request: Request):
    return request.app.state.calendar_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


def _safe_job_attachment_path(request: Request, job_id: str, filename: str) -> Path:
    path = request.app.state.calendar_store.upload_root / job_id / "job" / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return path


def _safe_completion_attachment_path(request: Request, job_id: str, form_id: str, filename: str) -> Path:
    path = request.app.state.calendar_store.upload_root / job_id / "completion" / form_id / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return path


class JobCreate(BaseModel):
    kind: str
    date: str
    status: Optional[str] = None

    customer: Optional[str] = ""
    contact: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""

    estimate_number: Optional[str] = ""
    invoice_number: Optional[str] = ""
    po_number: Optional[str] = ""

    job_notes: Optional[str] = ""
    office_notes: Optional[str] = ""
    job_number: Optional[str] = ""
    parts_order: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    kind: Optional[str] = None
    job_number: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None

    customer: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

    estimate_number: Optional[str] = None
    invoice_number: Optional[str] = None
    po_number: Optional[str] = None

    job_notes: Optional[str] = None
    office_notes: Optional[str] = None
    completion_forms: Optional[List[Dict[str, Any]]] = None
    parts_order: Optional[Dict[str, Any]] = None


class CompletionCreate(BaseModel):
    form_date: Optional[str] = ""
    technician_name: Optional[str] = ""
    door_type: Optional[str] = ""
    door_location: Optional[str] = ""

    time_onsite_hours: Optional[float] = None

    tech_notes: Optional[str] = ""
    parts_used: Optional[str] = ""
    additional_recommendations: Optional[str] = ""

    recommendations: Optional[str] = ""
    parts_required: Optional[str] = ""
    time_required: Optional[str] = ""
    ready_to_quote: Optional[bool] = False

    status_update: Optional[str] = ""


class CompletionUpdate(CompletionCreate):
    pass


@router.get("/jobs")
def list_jobs(
    request: Request,
    x_api_key: Optional[str] = Header(default=None),
    date: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
):
    _require(request, x_api_key)
    try:
        jobs = _store(request).query_jobs(date=date, status=status, q=q, limit=limit)
        return {"ok": True, "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    job = _store(request).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job": job}


@router.post("/jobs")
def create_job(request: Request, payload: JobCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        job = _store(request).create_job(payload.dict())
        return {"ok": True, "job": job}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/jobs/{job_id}")
def update_job(request: Request, job_id: str, payload: JobUpdate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        job = _store(request).update_job(job_id, payload.dict(exclude_unset=True))
        return {"ok": True, "job": job}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jobs/{job_id}")
def delete_job(request: Request, job_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        _store(request).delete_job(job_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/checkin/start")
def start_checkin(request: Request, job_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        job = _store(request).start_check_in(job_id)
        return {"ok": True, "job": job}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/checkin/stop")
def stop_checkin(request: Request, job_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        job = _store(request).stop_check_in(job_id)
        return {"ok": True, "job": job}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/completion")
def add_completion(request: Request, job_id: str, payload: CompletionCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        form = _store(request).add_completion_form(job_id, payload.dict(exclude_unset=True))
        return {"ok": True, "form": form}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/jobs/{job_id}/completion/{form_id}")
def update_completion(
    request: Request,
    job_id: str,
    form_id: str,
    payload: CompletionUpdate,
    x_api_key: Optional[str] = Header(default=None),
):
    _require(request, x_api_key)
    try:
        form = _store(request).update_completion_form(job_id, form_id, payload.dict(exclude_unset=True))
        return {"ok": True, "form": form}
    except KeyError:
        raise HTTPException(status_code=404, detail="Completion form not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/attachments")
async def upload_job_attachments(
    request: Request,
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
    files: List[UploadFile] = File(...),
):
    _require(request, x_api_key)
    try:
        blobs: List[Tuple[str, bytes]] = []
        for f in files:
            name = (f.filename or "upload").replace("/", "_").replace("\\", "_")
            blobs.append((name, await f.read()))
        saved = _store(request).add_job_attachments(job_id, blobs)
        return {"ok": True, "files": saved}
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/attachments/{filename}")
def get_job_attachment(
    request: Request,
    job_id: str,
    filename: str,
    x_api_key: Optional[str] = Header(default=None),
    inline: bool = Query(default=False),
):
    _require(request, x_api_key)
    path = _safe_job_attachment_path(request, job_id, filename)
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    headers = {"Content-Disposition": f"inline; filename=\"{path.name}\""} if inline else None
    return FileResponse(path=str(path), media_type=media_type, filename=None if inline else path.name, headers=headers)


@router.post("/jobs/{job_id}/completion/{form_id}/attachments")
async def upload_completion_attachments(
    request: Request,
    job_id: str,
    form_id: str,
    x_api_key: Optional[str] = Header(default=None),
    files: List[UploadFile] = File(...),
):
    _require(request, x_api_key)
    try:
        blobs: List[Tuple[str, bytes]] = []
        for f in files:
            name = (f.filename or "upload").replace("/", "_").replace("\\", "_")
            blobs.append((name, await f.read()))
        saved = _store(request).add_completion_attachments(job_id, form_id, blobs)
        return {"ok": True, "files": saved}
    except KeyError:
        raise HTTPException(status_code=404, detail="Completion form not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}/completion/{form_id}/attachments/{filename}")
def get_completion_attachment(
    request: Request,
    job_id: str,
    form_id: str,
    filename: str,
    x_api_key: Optional[str] = Header(default=None),
    inline: bool = Query(default=False),
):
    _require(request, x_api_key)
    path = _safe_completion_attachment_path(request, job_id, form_id, filename)
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    headers = {"Content-Disposition": f"inline; filename=\"{path.name}\""} if inline else None
    return FileResponse(path=str(path), media_type=media_type, filename=None if inline else path.name, headers=headers)
