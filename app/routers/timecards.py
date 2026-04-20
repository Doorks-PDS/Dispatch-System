from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/timecards", tags=["timecards"])


def _store(request: Request):
    return request.app.state.timecards_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


def _auth_user(request: Request):
    return getattr(request.state, "auth_user", None)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or ((_auth_user(request) or {}).get("role") or ""))


def _self_name(request: Request) -> str:
    user = _auth_user(request) or {}
    return str(user.get("name") or user.get("username") or "").strip()


class TimeCardCreate(BaseModel):
    technician_name: str = ""
    date: str = ""
    start_time: str = ""
    end_time: str = ""
    lunch_taken: bool = False
    lunch_start: str = ""
    lunch_end: str = ""
    notes: str = ""
    supervisor_approved: bool = False
    supervisor_approved_at: str = ""


@router.get("")
def list_timecards(request: Request, x_api_key: Optional[str] = Header(default=None), technician: Optional[str] = None, month: Optional[str] = None, limit: int = 500):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    if role in {"tech", "lead"}:
        technician = _self_name(request)
    items = _store(request).list(technician=technician, month=month, limit=limit)
    return {"ok": True, "items": items}


@router.post("")
def create_timecard(request: Request, payload: TimeCardCreate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    if not payload.date:
        raise HTTPException(status_code=400, detail="Missing date")
    data = payload.dict()
    if role in {"tech", "lead"}:
        data["technician_name"] = _self_name(request)
    item = _store(request).create(data)
    return {"ok": True, "item": item}


@router.put("/{item_id}")
def update_timecard(request: Request, item_id: str, payload: TimeCardCreate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    data = payload.dict()
    if role in {"tech", "lead"}:
        data["technician_name"] = _self_name(request)
        # tech/lead cannot self-approve via payroll style action
        data["supervisor_approved"] = False
        data["supervisor_approved_at"] = ""
    item = _store(request).update(item_id, data)
    return {"ok": True, "item": item}

@router.delete("/{item_id}")
def delete_timecard(request: Request, item_id: str, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    if role in {"tech", "lead"}:
        own = _self_name(request).lower()
        items = _store(request).list(limit=5000)
        target = next((x for x in items if str(x.get("id") or "") == str(item_id)), None)
        if not target or str(target.get("technician_name") or target.get("employee_name") or target.get("employee") or "").strip().lower() != own:
            raise HTTPException(status_code=403, detail="You can only delete your own time cards")
    _store(request).delete(item_id)
    return {"ok": True}
