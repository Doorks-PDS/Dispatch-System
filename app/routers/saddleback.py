from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/saddleback", tags=["saddleback"])


def _store(request: Request):
    return request.app.state.saddleback_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key, request)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or "")


def _can_write(request: Request) -> bool:
    return _auth_role(request) in {"admin", "office_admin"}


class SaddlebackPayload(BaseModel):
    orders: Optional[List[Dict[str, Any]]] = None
    expenses: Optional[List[Dict[str, Any]]] = None
    purchases: Optional[List[Dict[str, Any]]] = None


@router.get("")
def get_saddleback(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "data": _store(request).get_all()}


@router.put("")
def save_saddleback(request: Request, payload: SaddlebackPayload, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    if not _can_write(request):
        raise HTTPException(status_code=403, detail="Only office admin users can save Saddleback data")
    return {"ok": True, "data": _store(request).replace_all(payload.dict(exclude_unset=True))}
