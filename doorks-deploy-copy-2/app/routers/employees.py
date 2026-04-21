from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/employees", tags=["employees"])


ROLES = {"tech", "lead", "office", "office_admin"}


def _store(request: Request):
    return request.app.state.employees_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key, request=request)


class EmployeeCreate(BaseModel):
    name: str = ""
    role: str = "tech"
    phone: str = ""
    email: str = ""
    address: str = ""
    password: str = ""


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None


@router.get("")
def list_employees(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    items = list(_store(request).list())
    users_store = getattr(request.app.state, "users_store", None)
    user_by_name = {}
    if users_store:
        for user in users_store.list_users():
            if not isinstance(user, dict):
                continue
            name = str(user.get("name") or user.get("username") or "").strip()
            if not name:
                continue
            user_by_name[name.lower()] = user

    seen = set()
    merged = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        key = name.lower()
        user = user_by_name.get(key)
        row = dict(item)
        if user:
            row["role"] = str(user.get("role") or row.get("role") or "tech")
            if not row.get("email"):
                row["email"] = str(user.get("email") or "")
            row["login_user_id"] = user.get("id", "")
            row["login_username"] = user.get("username", "")
            row["login_active"] = bool(user.get("active", True))
        merged.append(row)
        if key:
            seen.add(key)

    if users_store:
        for user in users_store.list_users():
            if not isinstance(user, dict):
                continue
            name = str(user.get("name") or user.get("username") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            merged.append({
                "id": user.get("id", ""),
                "name": name,
                "role": user.get("role", "tech"),
                "phone": "",
                "email": str(user.get("email") or ""),
                "address": "",
                "login_user_id": user.get("id", ""),
                "login_username": user.get("username", ""),
                "login_active": bool(user.get("active", True)),
            })
            seen.add(key)

    merged.sort(key=lambda x: str((x.get("name") or "")).lower())
    return {"ok": True, "items": merged}


@router.post("")
def create_employee(request: Request, payload: EmployeeCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).create(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}


@router.put("/{emp_id}")
def update_employee(request: Request, emp_id: str, payload: EmployeeUpdate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    body = payload.model_dump(exclude_unset=True)
    if "role" in body:
        role = str(body.get("role") or "").strip().lower()
        if role and role not in ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
    try:
        item = _store(request).update(emp_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"ok": True, "item": item}


@router.delete("/{emp_id}")
def delete_employee(request: Request, emp_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    _store(request).delete(emp_id)
    return {"ok": True}
