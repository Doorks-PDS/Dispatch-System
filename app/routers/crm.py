from __future__ import annotations
 
from typing import Optional
 
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
 
router = APIRouter(prefix="/crm", tags=["crm"])
 
 
def _store(request: Request):
    return request.app.state.crm_store
 
 
def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key)
 
 
class CustomerCreate(BaseModel):
    company_name: str = ""
 
 
class ContactCreate(BaseModel):
    name: str = ""
    company_name: str = ""
    phone_number: str = ""
    cell_phone: str = ""
    email: str = ""

class CustomerUpdate(BaseModel):
    company_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone_number: str = ""
    email: str = ""
    notes: str = ""

class ContactUpdate(BaseModel):
    name: str = ""
    company_name: str = ""
    phone_number: str = ""
    cell_phone: str = ""
    email: str = ""
    title: str = ""
    notes: str = ""
 
 
@router.get("/customers")
def list_customers(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "items": _store(request).list_customers()}
 
 
@router.post("/customers")
def create_customer(request: Request, payload: CustomerCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).create_customer(payload.company_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}
 
 
@router.get("/contacts")
def list_contacts(
    request: Request,
    company_name: Optional[str] = None,
    x_api_key: Optional[str] = Header(default=None)
):
    _require(request, x_api_key)
    return {"ok": True, "items": _store(request).list_contacts(company_name=company_name)}
 
 
@router.post("/contacts")
def create_contact(request: Request, payload: ContactCreate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).create_contact(payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "item": item}


@router.put("/customers/{item_id}")
def update_customer(request: Request, item_id: str, payload: CustomerUpdate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).update_customer(item_id, payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "item": item}


@router.put("/contacts/{item_id}")
def update_contact(request: Request, item_id: str, payload: ContactUpdate, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    try:
        item = _store(request).update_contact(item_id, payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "item": item}
