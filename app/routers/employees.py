from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/employees", tags=["employees"])


def _store(request: Request):
    return request.app.state.employees_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


class EmployeeCreate(BaseModel):
    name: str = ""
    role: str = "tech"
    phone: str = ""
    email: str = ""
    address: str = ""
    password: str = ""


@router.get("")
def list_employees(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    base_items = list(_store(request).list())
    users_store = getattr(request.app.state, "users_store", None)

    def _norm(value: object) -> str:
        return str(value or "").strip().lower()

    items = []
    by_key = {}

    for item in base_items:
        if not isinstance(item, dict):
            continue
        merged = dict(item)
        name_key = _norm(merged.get("name"))
        email_key = _norm(merged.get("email"))
        key = (email_key or name_key)
        if key:
            by_key[key] = merged
        items.append(merged)

    if users_store:
        for user in users_store.list_users():
            if not isinstance(user, dict):
                continue
            name = str(user.get("name") or user.get("username") or "").strip()
            if not name:
                continue
            email = str(user.get("email") or "").strip()
            key = (_norm(email) or _norm(name))
            existing = by_key.get(key)
            if existing is not None:
                existing["role"] = user.get("role", existing.get("role", "tech"))
                existing["email"] = email or str(existing.get("email") or "")
                existing["login_user_id"] = user.get("id", "")
                existing["login_active"] = bool(user.get("active", True))
                existing["login_username"] = user.get("username", "")
                continue

            merged = {
                "id": user.get("id", ""),
                "name": name,
                "role": user.get("role", "tech"),
                "phone": "",
                "email": email,
                "address": "",
                "login_user_id": user.get("id", ""),
                "login_active": bool(user.get("active", True)),
                "login_username": user.get("username", ""),
            }
            items.append(merged)
            if key:
                by_key[key] = merged

    items.sort(key=lambda x: str((x.get("name") or "")).lower())
    return {"ok": True, "items": items}


@router.post("")
def create_employee(request: Request, payload: EmployeeCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).create(payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}


@router.delete("/{emp_id}")
def delete_employee(request: Request, emp_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    _store(request).delete(emp_id)
    return {"ok": True}


from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.services.storage import bootstrap_data_file


def _session_path(request: Request) -> Path:
    return bootstrap_data_file(Path(request.app.state.project_root), "employee_sessions.json")


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _ensure_admin(request: Request):
    store = _store(request)
    items = store.list()
    if any(str(x.get("role") or "").lower() == "admin" for x in items):
        return
    try:
        store.create({"name":"Jason","role":"admin","phone":"6829","email":"","address":"","password":"admin123"})
    except Exception:
        pass


class LoginPayload(BaseModel):
    username: str = ""
    password: str = ""


class VerifyPayload(BaseModel):
    username: str = ""
    pin: str = ""


@router.post('/login')
def login_employee(request: Request, payload: LoginPayload):
    _ensure_admin(request)
    username = (payload.username or '').strip().lower()
    password = (payload.password or '').strip()
    for item in _store(request).list():
        name = str(item.get('name') or '').strip().split(' ')[0].lower()
        if name == username and str(item.get('password') or '') == password:
            return {"ok": True, "requires_2fa": True, "name": item.get('name'), "role": item.get('role', 'tech')}
    raise HTTPException(status_code=401, detail='Invalid username or password')


@router.post('/verify-2fa')
def verify_2fa(request: Request, payload: VerifyPayload):
    _ensure_admin(request)
    username = (payload.username or '').strip().lower()
    pin = ''.join(ch for ch in str(payload.pin or '') if ch.isdigit())[-4:]
    for item in _store(request).list():
        name = str(item.get('name') or '').strip().split(' ')[0].lower()
        phone = ''.join(ch for ch in str(item.get('phone') or '') if ch.isdigit())[-4:]
        if name == username and phone == pin:
            token = f"sess-{item.get('id')}"
            now = datetime.now(timezone.utc)
            sessions = _read_json(_session_path(request), {"items": []})
            rows = [x for x in sessions.get('items', []) if x.get('token') != token]
            rows.append({"token": token, "employee_id": item.get('id'), "name": item.get('name'), "role": item.get('role', 'tech'), "created_at": now.isoformat(), "expires_at": (now + timedelta(hours=8)).isoformat(), "last_seen_at": now.isoformat()})
            _write_json(_session_path(request), {"items": rows})
            return {"ok": True, "token": token, "employee": {"id": item.get('id'), "name": item.get('name'), "role": item.get('role', 'tech')}}
    raise HTTPException(status_code=401, detail='Invalid verification pin')


@router.post('/logout')
def logout_employee(request: Request, token: str = ''):
    sessions = _read_json(_session_path(request), {"items": []})
    sessions['items'] = [x for x in sessions.get('items', []) if str(x.get('token')) != str(token)]
    _write_json(_session_path(request), sessions)
    return {"ok": True}


@router.get('/me')
def employee_me(request: Request, token: str = ''):
    sessions = _read_json(_session_path(request), {"items": []})
    now = datetime.now(timezone.utc)
    for row in sessions.get('items', []):
        if str(row.get('token')) != str(token):
            continue
        try:
            expires = datetime.fromisoformat(str(row.get('expires_at')))
            last_seen = datetime.fromisoformat(str(row.get('last_seen_at')))
        except Exception:
            continue
        if now > expires or now - last_seen > timedelta(minutes=45):
            raise HTTPException(status_code=401, detail='Session expired')
        row['last_seen_at'] = now.isoformat()
        _write_json(_session_path(request), sessions)
        return {"ok": True, "employee": {"id": row.get('employee_id'), "name": row.get('name'), "role": row.get('role')}}
    raise HTTPException(status_code=401, detail='Not logged in')
