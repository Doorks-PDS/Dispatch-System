from fastapi import APIRouter, Request
from typing import Any, Dict
from pydantic import BaseModel

router = APIRouter()

class PricingUpdate(BaseModel):
    trip: float = 190
    fuel: float = 20
    labor: float = 190
    crew_labor: float = 250
    tax: float = 7.75
    default_terms: str = "Due on Receipt"
    billing_terms: list[str] = []
    tax_cities: list[Dict[str, Any]] = []

@router.get("/pricing")
def get_pricing(request: Request):
    if not getattr(request.state, "auth_user", None):
        request.app.state.require_key(None)
    return request.app.state.pricing_store.load()

@router.put("/pricing")
def update_pricing(data: PricingUpdate, request: Request):
    if not getattr(request.state, "auth_user", None):
        request.app.state.require_key(None)
    request.app.state.pricing_store.save(data.dict())
    return {"ok": True}
