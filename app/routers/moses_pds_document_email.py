"""PDS document email workflow: preview -> proposal -> approved Resend send."""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from app.services import moses_pds_document_email as delivery

router = APIRouter(prefix='/moses-pds-email', tags=['moses-pds-email'])

class Approval(BaseModel):
    approve: bool

class Recipients(BaseModel):
    to: str | list[str] = Field(max_length=1500)
    cc: str | list[str] = Field(default='', max_length=1500)

@router.get('/review-queue')
def review_queue(request: Request):
    return delivery.review_queue(request)

@router.get('/{kind}/{number}/preview')
def preview(kind: str, number: str, request: Request):
    return delivery.preview(request, kind, number)

@router.post('/{kind}/{number}/proposal')
def propose(kind: str, number: str, request: Request, payload: Recipients | None = None):
    return delivery.propose(request, kind, number, payload.model_dump() if payload else None)

@router.post('/proposals/{proposal_id}/decision')
def decide(proposal_id: str, payload: Approval, request: Request):
    return delivery.decide(request, proposal_id, payload.approve)

@router.get('/{kind}/{number}/history')
def history(kind: str, number: str, request: Request):
    return {'items': delivery.history(request, kind, number)}
