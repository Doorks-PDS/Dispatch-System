from fastapi import APIRouter, Request
from typing import Any, Dict
from pydantic import BaseModel

router = APIRouter()

class PricingUpdate(BaseModel):
    trip: float = 175
    fuel: float = 20
    labor: float = 175
    crew_labor: float = 235
    tax: float = 7.75
    default_terms: str = "Due on Receipt"
    billing_terms: list[str] = []
    tax_cities: list[Dict[str, Any]] = []

@router.get("/pricing")
def get_pricing(request: Request):
    return request.app.state.pricing_store.load()

@router.put("/pricing")
def update_pricing(data: PricingUpdate, request: Request):
    request.app.state.pricing_store.save(data.dict())
    return {"ok": True}
