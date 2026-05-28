from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/document-approvals", tags=["document-approvals"])


def _store(request: Request):
    return request.app.state.document_approvals_store


def _require(request: Request, x_api_key: Optional[str]) -> str:
    return str(request.app.state.require_key(x_api_key, request) or "")


def _can_write(role: str) -> bool:
    return str(role or "") in {"admin", "office_admin", "office", "lead"}


class ApprovalPayload(BaseModel):
    approved: bool = False
    approved_at: Optional[str] = ""
    estimate_number: Optional[str] = ""
    filename: Optional[str] = ""
    customer: Optional[str] = ""


@router.get("")
def get_document_approvals(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "approvals": _store(request).get_all()}


@router.put("/{key}")
def set_document_approval(key: str, request: Request, payload: ApprovalPayload, x_api_key: Optional[str] = Header(default=None)):
    role = _require(request, x_api_key)
    if not _can_write(role):
        raise HTTPException(status_code=403, detail="Only office/admin/lead users can update estimate approval status")
    try:
        return {"ok": True, "approval": _store(request).set_approval(key, payload.dict())}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
