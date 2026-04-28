from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/addresses", tags=["addresses"])


class AddressCreate(BaseModel):
    address: str
    customer: str = ""
    company_name: str = ""
    customer_id: str = ""
    label: str = ""
    notes: str = ""


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)


def _store(request: Request):
    return request.app.state.address_store


@router.get("")
def list_addresses(
    request: Request,
    q: str = Query(default=""),
    limit: int = Query(default=1000, ge=1, le=5000),
    include_legacy: bool = Query(default=True),
    saved_only: bool = Query(default=False),
    x_api_key: Optional[str] = Header(default=None),
):
    _require(request, x_api_key)
    return {"ok": True, "items": _store(request).list(q=q, limit=limit, include_legacy=include_legacy, saved_only=saved_only)}


@router.post("")
def create_address(request: Request, payload: AddressCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).create(payload.dict())
        return {"ok": True, "item": item}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{item_id}")
def update_address(request: Request, item_id: str, payload: AddressCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).update(item_id, payload.dict())
        return {"ok": True, "item": item}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{item_id}")
def delete_address(request: Request, item_id: str, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        _store(request).delete(item_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
