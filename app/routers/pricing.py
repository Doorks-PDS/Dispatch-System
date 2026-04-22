from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class PricingUpdate(BaseModel):
    trip: float
    fuel: float
    labor: float
    crew_labor: float
    tax: float

@router.get("/pricing")
def get_pricing(request: Request):
    return request.app.state.pricing_store.load()

@router.put("/pricing")
def update_pricing(data: PricingUpdate, request: Request):
    request.app.state.pricing_store.save(data.dict())
    return {"ok": True}
