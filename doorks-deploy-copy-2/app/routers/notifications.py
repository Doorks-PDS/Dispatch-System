from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _store(request: Request):
    return request.app.state.notifications_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


def _auth_user(request: Request):
    return getattr(request.state, "auth_user", None)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or ((_auth_user(request) or {}).get("role") or ""))


class NotifCreate(BaseModel):
    to: str = ""
    message: str = ""
    from_: str = ""  # legacy fallback


class NotifReadUpdate(BaseModel):
    read: bool = True


@router.get("")
def list_notifications(request: Request, x_api_key: Optional[str] = Header(default=None), limit: int = 200):
    user = _auth_user(request)
    if user:
        return {"ok": True, "items": _store(request).list_for(user, limit=limit)}
    _require(request, x_api_key)
    return {"ok": True, "items": _store(request).list(limit=limit)}


@router.get("/recipients")
def list_recipients(request: Request, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    if not user:
        _require(request, x_api_key)
        raise HTTPException(status_code=401, detail="Login required")
    users_store = getattr(request.app.state, "users_store", None)
    if users_store is None:
        return {"ok": True, "items": []}
    items = []
    for item in users_store.list_users():
        if not bool(item.get("active", True)):
            continue
        items.append({
            "id": item.get("id", ""),
            "username": item.get("username", ""),
            "name": item.get("name", ""),
            "role": item.get("role", "tech"),
        })
    return {"ok": True, "items": items}


@router.post("")
def create_notification(request: Request, payload: NotifCreate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    if user:
        sender = str(user.get("username") or "").strip() or str(user.get("id") or "").strip()
        item = _store(request).create({
            "to": payload.to,
            "message": payload.message,
            "from": sender,
            "from_name": str(user.get("name") or user.get("username") or "").strip(),
            "to_name": "",
        })
        return {"ok": True, "item": item}
    _require(request, x_api_key)
    item = _store(request).create({"to": payload.to, "message": payload.message, "from": payload.from_})
    return {"ok": True, "item": item}


@router.put("/{notif_id}/read")
def mark_read(request: Request, notif_id: str, payload: NotifReadUpdate, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    try:
        if user:
            item = _store(request).mark_read(notif_id, user, read=payload.read)
            return {"ok": True, "item": item}
        _require(request, x_api_key)
        raise HTTPException(status_code=401, detail="Login required")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except KeyError:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.delete("/{notif_id}")
def delete_notification(request: Request, notif_id: str, x_api_key: Optional[str] = Header(default=None)):
    user = _auth_user(request)
    try:
        if user:
            _store(request).delete(notif_id, viewer=user, allow_admin=_auth_role(request) == "office_admin")
            return {"ok": True}
        _require(request, x_api_key)
        _store(request).delete(notif_id)
        return {"ok": True}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except KeyError:
        raise HTTPException(status_code=404, detail="Notification not found")
