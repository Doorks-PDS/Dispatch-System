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


@router.get('/payment-fee-plan')
def payment_fee_plan(request: Request):
    from app.services import pds_payment_fee_plan as plan
    return plan.summary(request)

@router.get('/payment-fee-plan/invoices/{invoice_number}')
def payment_fee_invoice_preview(invoice_number: str, request: Request):
    from app.services import pds_payment_fee_plan as plan
    return plan.invoice_preview(request, invoice_number)

@router.get('/sync-preview/invoices/{invoice_number}')
def sync_invoice_preview(invoice_number: str, request: Request):
    from app.services import pds_quickbooks_sync_preview as preview_service
    return preview_service.preview_invoice(request, invoice_number)

@router.get('/sync-preview/purchase-orders/{po_number}')
def sync_po_preview(po_number: str, request: Request):
    from app.services import pds_quickbooks_sync_preview as preview_service
    return preview_service.preview_supplier_po(request, po_number)

# 5.73: QuickBooks Online authorization and *read-only* verification.
# No supplier PO / invoice / payment mutation is reachable through these routes.
class ConnectConfirmation(BaseModel):
    confirm: bool = False

@router.get('/connection-status')
def qbo_connection_status(request: Request):
    from app.services import pds_qbo_connection as conn
    return conn.configuration(request)

@router.post('/oauth/start')
def qbo_oauth_start(payload: ConnectConfirmation, request: Request):
    from fastapi import HTTPException
    from app.services import pds_qbo_connection as conn
    conn.qb._admin(request, mutation=True)
    if not payload.confirm:
        raise HTTPException(422, 'Confirm QuickBooks Online authorization')
    return conn.authorization_url(request)

@router.get('/oauth/callback')
def qbo_oauth_callback(request: Request, code: str = '', state: str = '', realmId: str = '', error: str = ''):
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse
    from app.services import pds_qbo_connection as conn
    conn.qb._admin(request, mutation=True)
    if error:
        request.session.pop(conn.SESSION_KEY, None)
        raise HTTPException(409, 'QuickBooks authorization was not completed')
    conn.finish_authorization(request, code=code, state=state, realm_id=realmId)
    return RedirectResponse('/?quickbooks=authorized', status_code=303, headers={'Cache-Control': 'no-store'})

@router.post('/verify-company')
def qbo_verify_company(payload: ConnectConfirmation, request: Request):
    from fastapi import HTTPException
    from app.services import pds_qbo_connection as conn
    conn.qb._admin(request)
    if not payload.confirm:
        raise HTTPException(422, 'Confirm read-only company verification')
    return conn.verify_company(request)

@router.post('/disconnect-local')
def qbo_disconnect_local(payload: ConnectConfirmation, request: Request):
    from fastapi import HTTPException
    from app.services import pds_qbo_connection as conn
    conn.qb._admin(request, mutation=True)
    if not payload.confirm:
        raise HTTPException(422, 'Confirm removal of local QuickBooks authorization')
    return conn.disconnect_local(request)

@router.get('/sync-readiness')
def qbo_sync_readiness(request: Request):
    from app.services import pds_qbo_connection as conn
    from app.services import pds_quickbooks_purchase_orders as pos
    from app.services import pds_quickbooks_numbering as numbering_service
    conn.qb._admin(request)
    c = conn.configuration(request)
    invoices = conn.qb.preview(request)['invoices']
    purchase_orders = pos.preview(request)['purchase_orders']
    plan = numbering_service.get_plan(request)
    verified = bool(c['authorized'] and c['last_read_only_verification'])
    def tally(records):
        return {'total': len(records),
                'prepared': sum(x.get('handoff_status') == 'prepared_for_review' for x in records),
                'needs_review': sum(bool(x.get('needs_review')) for x in records),
                'linked_to_provider': 0}
    return {'company_verified_read_only': verified,
            'edition': c['edition'], 'environment': c['environment'],
            'company_name': c['company_name'], 'company_id': c['company_id'],
            'invoices': tally(invoices), 'supplier_purchase_orders': tally(purchase_orders),
            'numbering_plan_saved': bool(plan['saved']),
            'required_before_posting': [
                'Confirm the correct PDS QuickBooks company and accounting plan',
                'Verify customer and vendor IDs with provider records',
                'Verify income, expense, items and tax mapping',
                'Check existing QuickBooks DocNumbers for collisions',
                'Approve a single invoice and PO test with an accountant',
                'Confirm payment processor costs and accepted payment methods',
            ],
            'provider_transaction_posting_enabled': False,
            'automatic_sync_enabled': False, 'payment_link_enabled': False,
            'service_fee_rate_percent': '0.00', 'service_fee_live': False}

# 5.74: bounded provider lookup to review customer/vendor/item/account mappings.
# Strictly Office Admin read-only; no accounting writes or saved mapping guesses.
@router.get('/provider-catalog/{kind}')
def qbo_provider_catalog(kind: str, request: Request, start: int = 1, limit: int = 100):
    from app.services import pds_qbo_catalog as catalog_service
    return catalog_service.catalog(request, kind, start=start, limit=limit)


# Moses 5.75: prepared-source, read-only DocNumber duplicate check.
@router.get('/provider-duplicate-check/{kind}/{number}')
def qbo_provider_duplicate_check(kind: str, number: str, request: Request):
    from app.services import pds_qbo_collision_check as checker
    return checker.check(request, kind, number)


# 5.76: non-persistent read-only source party comparison; never auto-maps.
@router.get('/provider-party-review/{kind}/{number}')
def qbo_provider_party_review(kind: str, number: str, request: Request, start: int = 1, limit: int = 100):
    from app.services import pds_qbo_match_review as reviewer
    return reviewer.review(request, kind, number, start=start, limit=limit)


# Moses 5.77: admin-reviewed party identity receipts. Never posts to QuickBooks.
class PartyApproval(BaseModel):
    provider_id: str = Field(min_length=1, max_length=32)
    confirm: bool = False

@router.get('/party-mapping/{kind}/{number}')
def party_mapping_status(kind: str, number: str, request: Request):
    from app.services import pds_qbo_party_mappings as mapping
    return mapping.status(request, kind, number)

@router.post('/party-mapping/{kind}/{number}')
def party_mapping_approve(kind: str, number: str, payload: PartyApproval, request: Request):
    from app.services import pds_qbo_party_mappings as mapping
    return mapping.approve(request, kind, number, payload.provider_id, confirm=payload.confirm)


# Moses 5.78: PDS customer, service-vendor, and parts master links.
# Existing records stay intact; accounting transaction posting remains disabled.
class MasterLinkApproval(BaseModel):
    provider_id: str = Field(min_length=1, max_length=32)
    confirm: bool = False

@router.get('/master-links/{kind}')
def qbo_master_links(kind: str, request: Request, start: int = 0, limit: int = 100):
    from app.services import pds_qbo_master_links as master
    return master.overview(request, kind, start=start, limit=limit)

@router.get('/master-links/{kind}/{pds_id}/candidates')
def qbo_master_candidates(kind: str, pds_id: str, request: Request, start: int = 1, limit: int = 100):
    from app.services import pds_qbo_master_links as master
    return master.candidates(request, kind, pds_id, start=start, limit=limit)

@router.post('/master-links/{kind}/{pds_id}/approve')
def qbo_master_approve(kind: str, pds_id: str, payload: MasterLinkApproval, request: Request):
    from app.services import pds_qbo_master_links as master
    return master.approve(request, kind, pds_id, payload.provider_id, confirm=payload.confirm)

# 5.79: reconciled master identity preview; no provider write operations.
@router.get('/sync-readiness/invoices/{invoice_number}')
def qbo_invoice_readiness(invoice_number: str, request: Request):
    from app.services import pds_qbo_sync_readiness as readiness
    return readiness.readiness(request, 'invoice', invoice_number)

@router.get('/sync-readiness/purchase-orders/{po_number}')
def qbo_po_readiness(po_number: str, request: Request):
    from app.services import pds_qbo_sync_readiness as readiness
    return readiness.readiness(request, 'supplier_po', po_number)

# Moses 5.81: verified per-line QBO item references; no provider transaction writes.
class LineItemApproval(BaseModel):
    provider_id: str = Field(min_length=1, max_length=32)
    confirm: bool = False

@router.get('/line-mappings/{kind}/{number}')
def qbo_line_mapping_status(kind: str, number: str, request: Request):
    from app.services import pds_qbo_line_mappings as mapper
    return mapper.status(request, kind, number)

@router.post('/line-mappings/{kind}/{number}/lines/{position}/approve')
def qbo_approve_line_item(kind: str, number: str, position: int, payload: LineItemApproval, request: Request):
    from app.services import pds_qbo_line_mappings as mapper
    return mapper.approve(request, kind, number, position, payload.provider_id, confirm=payload.confirm)


# Moses 5.82: one-document dry-run worksheet; read only, no provider writes.
@router.get('/trial-readiness/{kind}/{number}')
def qbo_trial_readiness(kind: str, number: str, request: Request):
    from app.services import pds_qbo_trial_plan as trial
    return trial.report(request, kind, number)

# 5.83: read-only, redacted connection diagnostics and one-document trial packet.
@router.get('/trial-setup-diagnostics')
def qbo_trial_setup_diagnostics(request: Request):
    from app.services import pds_qbo_trial_packet as packet
    return packet.setup_diagnostics(request)

@router.get('/trial-packet/{kind}/{number}')
def qbo_trial_packet(kind: str, number: str, request: Request, check_duplicates: bool = False):
    from app.services import pds_qbo_trial_packet as packet
    return packet.packet(request, kind, number, check_duplicates=check_duplicates)

@router.get('/trial-packet/{kind}/{number}/download')
def qbo_download_trial_packet(kind: str, number: str, request: Request, check_duplicates: bool = False):
    from app.services import pds_qbo_trial_packet as packet
    import json
    from fastapi.responses import Response
    data = packet.packet(request, kind, number, check_duplicates=check_duplicates)
    safe_number = data['pds_number']
    return Response(json.dumps(data, indent=2), media_type='application/json', headers={
        'Content-Disposition': f'attachment; filename="PDS_QBO_TRIAL_{safe_number}.json"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    })

@router.get('/master-link-coverage')
def qbo_master_link_coverage(request: Request):
    from app.services import pds_qbo_trial_packet as packet
    return packet.mapping_coverage(request)
