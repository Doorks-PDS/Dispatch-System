from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/timeoff", tags=["timeoff"])


def _store(request: Request):
    return request.app.state.timeoff_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


def _auth_user(request: Request):
    return getattr(request.state, "auth_user", None)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or ((_auth_user(request) or {}).get("role") or ""))


def _self_name(request: Request) -> str:
    user = _auth_user(request) or {}
    return str(user.get("name") or user.get("username") or "").strip()


class TimeOffCreate(BaseModel):
    employee_name: str = ""
    start_date: str = ""
    end_date: str = ""
    notes: str = ""
    emergency: bool = False
    status: str = "pending"


class TimeOffUpdate(BaseModel):
    employee_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
    emergency: Optional[bool] = None
    status: Optional[str] = None


@router.get("")
def list_timeoff(request: Request, x_api_key: Optional[str] = Header(default=None), employee_name: str = Query(default=""), status: str = Query(default=""), limit: int = Query(default=500, ge=1, le=5000)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    if role in {"tech", "lead"}:
        employee_name = _self_name(request)
    return {"ok": True, "items": _store(request).list_items(employee_name=employee_name, status=status, limit=limit)}


@router.post("")
def create_timeoff(request: Request, payload: TimeOffCreate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    data = payload.dict()
    if role in {"tech", "lead"}:
        data["employee_name"] = _self_name(request)
        data["status"] = "pending"
    try:
        return {"ok": True, "item": _store(request).create_item(data)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{item_id}")
def update_timeoff(request: Request, item_id: str, payload: TimeOffUpdate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    update = payload.dict(exclude_unset=True)
    if role in {"tech", "lead"}:
        items = _store(request).list_items(employee_name=_self_name(request), limit=5000)
        target = next((x for x in items if str(x.get("id") or "") == str(item_id)), None)
        if not target:
            raise HTTPException(status_code=403, detail="You can only edit your own time off requests")
        if "status" in update:
            update.pop("status", None)
        update["employee_name"] = _self_name(request)
    try:
        return {"ok": True, "item": _store(request).update_item(item_id, update)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Time off request not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{item_id}")
def delete_timeoff(request: Request, item_id: str, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    role = _auth_role(request)
    if not user:
        _require(request, x_api_key)
    if role in {"tech", "lead"}:
        items = _store(request).list_items(employee_name=_self_name(request), limit=5000)
        target = next((x for x in items if str(x.get("id") or "") == str(item_id)), None)
        if not target:
            raise HTTPException(status_code=403, detail="You can only delete your own time off requests")
    try:
        _store(request).delete_item(item_id)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="Time off request not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
