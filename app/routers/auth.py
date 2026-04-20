from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

ROLES = ["office_admin", "office", "tech", "lead"]


class LoginRequest(BaseModel):
    username: str
    password: str


class PinRequest(BaseModel):
    pin: str


class UserCreateRequest(BaseModel):
    username: str
    name: str = ""
    email: str = ""
    role: str = "tech"
    password: str
    pin: str
    active: bool = True


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class PasswordUpdateRequest(BaseModel):
    password: str


class PinUpdateRequest(BaseModel):
    pin: str


class ActiveUpdateRequest(BaseModel):
    active: bool


def _store(request: Request):
    store = getattr(request.app.state, "users_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Users store not configured")
    return store


def _sanitize(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user.get("id", ""),
        "username": user.get("username", ""),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "tech"),
        "active": bool(user.get("active", True)),
    }


def _require_admin(request: Request) -> Dict[str, Any]:
    user = getattr(request.state, "auth_user", None)
    role = getattr(request.state, "auth_role", None)
    if not user or role != "office_admin":
        raise HTTPException(status_code=403, detail="Office admin access required")
    return user


@router.get("/me")
def auth_me(request: Request):
    user = getattr(request.state, "auth_user", None)
    if not user:
        return {"logged_in": False, "user": None, "roles": ROLES}
    return {"logged_in": True, "user": _sanitize(user), "roles": ROLES}


@router.post("/login")
def auth_login(payload: LoginRequest, request: Request):
    store = _store(request)
    raw_user = store.verify_password_only(payload.username, payload.password)
    if not raw_user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session.clear()
    user_id = str(raw_user.get("id", ""))
    request.session["pending_user_id"] = user_id

    if str(raw_user.get("pin_hash") or "").strip():
        return {"ok": True, "requires_pin": True, "user": _sanitize(raw_user)}

    safe_user = store.verify_pin(user_id, "")
    if not safe_user:
        raise HTTPException(status_code=401, detail="Unable to complete login")
    request.session.pop("pending_user_id", None)
    request.session["user_id"] = safe_user.get("id", "")
    return {"ok": True, "requires_pin": False, "user": safe_user}


@router.post("/login-pin")
def auth_login_pin(payload: PinRequest, request: Request):
    store = _store(request)
    pending_user_id = str(request.session.get("pending_user_id") or "").strip()
    if not pending_user_id:
        raise HTTPException(status_code=401, detail="Username/password step expired. Please start over.")
    user = store.verify_pin(pending_user_id, payload.pin)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    request.session.pop("pending_user_id", None)
    request.session["user_id"] = user.get("id", "")
    return {"ok": True, "user": user}


@router.post("/logout")
def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/users")
def list_users(request: Request):
    _require_admin(request)
    return {"ok": True, "items": [_sanitize(x) for x in _store(request).list_users()]}


@router.post("/users")
def create_user(payload: UserCreateRequest, request: Request):
    _require_admin(request)
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    pin = "".join(ch for ch in str(payload.pin or "") if ch.isdigit())[-4:]
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be 4 digits")
    try:
        item = _store(request).create_user(
            username=payload.username,
            name=payload.name or payload.username,
            email=payload.email,
            role=payload.role,
            password=payload.password,
            pin=pin,
            active=payload.active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": _sanitize(item)}


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateRequest, request: Request):
    _require_admin(request)
    try:
        item = _store(request).update_user(
            user_id,
            username=payload.username,
            name=payload.name,
            email=payload.email,
            role=payload.role,
            active=payload.active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "item": _sanitize(item)}


@router.put("/users/{user_id}/password")
def update_password(user_id: str, payload: PasswordUpdateRequest, request: Request):
    _require_admin(request)
    try:
        item = _store(request).set_password(user_id, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "item": _sanitize(item)}


@router.put("/users/{user_id}/pin")
def update_pin(user_id: str, payload: PinUpdateRequest, request: Request):
    _require_admin(request)
    pin = "".join(ch for ch in str(payload.pin or "") if ch.isdigit())[-4:]
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be 4 digits")
    try:
        item = _store(request).set_pin(user_id, pin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "item": _sanitize(item)}


@router.put("/users/{user_id}/active")
def update_active(user_id: str, payload: ActiveUpdateRequest, request: Request):
    current = _require_admin(request)
    if str(current.get("id") or "") == str(user_id) and payload.active is False:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    item = _store(request).set_active(user_id, payload.active)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "item": _sanitize(item)}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request):
    current = _require_admin(request)
    if str(current.get("id") or "") == str(user_id):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    try:
        ok = _store(request).delete_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
