from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/shared-settings", tags=["shared-settings"])


def _store(request: Request):
    return request.app.state.shared_settings_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key, request)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or "")


def _can_write(request: Request) -> bool:
    role = _auth_role(request)
    return role in {"admin", "office_admin", "office", "lead"}


class SharedSettingsUpdate(BaseModel):
    rollup_profiles: Optional[Dict[str, Any]] = None
    pto_bank: Optional[Dict[str, Any]] = None
    ot_bank: Optional[Dict[str, Any]] = None


@router.get("")
def get_shared_settings(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "settings": _store(request).get_all()}


@router.put("")
def update_shared_settings(request: Request, payload: SharedSettingsUpdate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    if not _can_write(request):
        raise HTTPException(status_code=403, detail="Only office/admin users can update shared settings")
    return {"ok": True, "settings": _store(request).update_all(payload.dict(exclude_unset=True))}


@router.put("/{section}")
def update_shared_settings_section(request: Request, section: str, payload: Dict[str, Any], x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    if not _can_write(request):
        raise HTTPException(status_code=403, detail="Only office/admin users can update shared settings")
    try:
        return {"ok": True, "settings": _store(request).update_section(section, payload)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
