"""Safe PDS invoice handoff preview; does not connect to or mutate QuickBooks."""
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal
from app.services import pds_quickbooks_bridge as qb

router = APIRouter(prefix='/pds-quickbooks', tags=['pds-quickbooks'])

class PrepareRequest(BaseModel):
    invoice_number: str = Field(min_length=7, max_length=20)
    fingerprint: str = Field(min_length=64, max_length=64)
    confirm: bool = False

class EditionSettings(BaseModel):
    edition: Literal['online', 'desktop', 'not_selected']
    confirm: bool = False

@router.post('/configuration')
def configuration(payload: EditionSettings, request: Request):
    if payload.confirm is not True:
        from fastapi import HTTPException
        raise HTTPException(422, 'Confirm QuickBooks edition selection')
    return qb.select_edition(request, payload.edition)

@router.get('/status')
def status(request: Request):
    return qb.status(request)

@router.get('/invoices')
def invoices(request: Request):
    return qb.preview(request)

@router.post('/prepare-invoice')
def prepare_invoice(payload: PrepareRequest, request: Request):
    if payload.confirm is not True:
        from fastapi import HTTPException
        raise HTTPException(422, 'Explicit confirmation required')
    return qb.prepare(request, payload.invoice_number, payload.fingerprint)

@router.get('/review.csv')
def review_csv(request: Request):
    content = qb.export_review_csv(request)
    return Response(content, media_type='text/csv', headers={
        'Content-Disposition': 'attachment; filename="PDS_QuickBooks_Invoice_Handoff_Review.csv"',
        'Cache-Control': 'no-store',
    })

class PreparePORequest(BaseModel):
    po_number: str = Field(min_length=8, max_length=30)
    fingerprint: str = Field(min_length=64, max_length=64)
    confirm: bool = False

@router.get('/purchase-orders')
def purchase_orders(request: Request):
    from app.services import pds_quickbooks_purchase_orders as po
    return po.preview(request)

@router.post('/prepare-po')
def prepare_po(payload: PreparePORequest, request: Request):
    from fastapi import HTTPException
    from app.services import pds_quickbooks_purchase_orders as po
    # Authentication takes priority over body confirmation.
    po.qb._admin(request, mutation=True)
    if payload.confirm is not True:
        raise HTTPException(422, 'Explicit confirmation required')
    return po.prepare(request, payload.po_number, payload.fingerprint)

@router.get('/po-review.csv')
def po_review_csv(request: Request):
    from app.services import pds_quickbooks_purchase_orders as po
    return Response(po.export_review_csv(request), media_type='text/csv', headers={
        'Content-Disposition': 'attachment; filename="PDS_QuickBooks_Supplier_PO_Handoff_Review.csv"',
        'Cache-Control': 'no-store',
    })


class NumberPlan(BaseModel):
    policies: dict[str, Literal['request_doorks_number', 'quickbooks_assigns_number']]
    confirm: bool = False

@router.get('/numbering')
def numbering(request: Request):
    from app.services import pds_quickbooks_numbering as numbering_service
    return numbering_service.get_plan(request)

@router.post('/numbering')
def save_numbering(payload: NumberPlan, request: Request):
    from app.services import pds_quickbooks_numbering as numbering_service
    numbering_service.qb._admin(request, mutation=True)
    if payload.confirm is not True:
        from fastapi import HTTPException
        raise HTTPException(422, 'Confirm QuickBooks numbering plan')
    return numbering_service.save_plan(request, payload.policies)
