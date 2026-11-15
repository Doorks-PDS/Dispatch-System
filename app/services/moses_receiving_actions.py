"""Moses approval-controlled PO receipts. Uses the existing receiving journal.

No supplier bill, payment, or live inventory mutation. An uncertain write is
reconciled from the journal using the stable proposal ID; it is never blindly
retried. All data is scoped to the active workspace.
"""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from fastapi import HTTPException
from app.routers import pds_purchase_orders as po_store
from app.services.moses_receiving_review import review
from app.services.doorks_po_lock import po_write_lock


def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(request):
    platform = request.session.get('active_platform')
    if platform not in ('pds', 'doorks', 'sdc') or not getattr(request.state, 'auth_user', None) or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active workspace office admin required')
    if os.getenv('MOSES_RECEIVING_ACTIONS_ENABLED', '').strip().lower() != 'true':
        raise HTTPException(503, 'Moses receiving actions disabled')
    po_store._receive_context(request, platform)
    return platform


def _path(request, platform):
    p = Path(request.app.state.data_dir) / 'moses_receiving' / platform
    p.mkdir(parents=True, exist_ok=True)
    return p / 'proposals.json'


def _rows(path):
    values = po_store._read(path, [])
    if not isinstance(values, list):
        raise HTTPException(500, 'Invalid receiving proposal store')
    return values


def _event(request, platform, proposal_id):
    return next((e for e in po_store._receive_events(request, platform)
                 if e.get('request_id') == 'moses-receive-' + proposal_id), None)


def _reconcile(request, platform, rows):
    changed = False
    for p in rows:
        if p.get('state') != 'executing':
            continue
        event = _event(request, platform, p['id'])
        p['state'] = 'executed' if event else 'needs_review'
        p['reconciled_at'] = _now()
        if event:
            p['receipt_id'] = event.get('id')
        changed = True
    if changed:
        po_store._write(_path(request, platform), rows)
    return rows


def propose(request, po_identifier: str, quantity: float, reference: str = '', notes: str = ''):
    platform = _guard(request)
    if not isinstance(reference, str) or len(reference) > 200 or not isinstance(notes, str) or len(notes) > 500:
        raise HTTPException(422, 'Invalid packing slip reference or notes')
    if not reference.strip():
        raise HTTPException(422, 'Packing slip reference required')
    with po_write_lock(request, platform), po_store._lock:
        summary = review(request, po_identifier, quantity)
        if summary['over_receipt']:
            raise HTTPException(409, 'Quantity exceeds outstanding order; review manually')
        if summary['outstanding_quantity'] == 0:
            raise HTTPException(409, 'Purchase order already fully received')
        # Prevent a second proposal for a packing slip already in the journal.
        if any(e.get('po_id') == summary['po_id'] and
               str(e.get('reference') or '').casefold() == reference.strip().casefold()
               for e in po_store._receive_events(request, platform)):
            raise HTTPException(409, 'Packing slip reference already received for this purchase order')
        path = _path(request, platform)
        rows = _reconcile(request, platform, _rows(path))
        if any(p.get('state') in ('pending', 'executing', 'needs_review') and
               p.get('po_id') == summary['po_id'] and str(p.get('reference') or '').casefold() == reference.strip().casefold() for p in rows):
            raise HTTPException(409, 'A receipt for this packing slip already awaits review')
        proposal = {'id': uuid.uuid4().hex, 'kind': 'receive_purchase_order',
                    'platform': platform, 'po_id': summary['po_id'],
                    'po_number': summary['po_number'], 'supplier': summary['supplier'],
                    'quantity': summary['packing_slip_quantity'], 'reference': reference.strip(),
                    'notes': notes.strip(), 'expected_received': summary['previously_received'],
                    'expected_outstanding': summary['outstanding_quantity'],
                    'discrepancy': summary['short_receipt'], 'state': 'pending',
                    'created_at': _now(), 'requested_by': str(request.state.auth_user)[:100]}
        rows.append(proposal)
        po_store._write(path, rows)
        return {'proposal': proposal, 'approval_required': True, 'executed': False,
                'note': 'Receiving journal only. No stock-on-hand or supplier bill change.'}


def pending(request):
    platform = _guard(request)
    with po_write_lock(request, platform), po_store._lock:
        rows = _reconcile(request, platform, _rows(_path(request, platform)))
        return {'proposals': [p for p in rows if p.get('state') in ('pending', 'needs_review')],
                'count': sum(p.get('state') in ('pending', 'needs_review') for p in rows)}


def decide(request, proposal_id: str, approve: bool):
    platform = _guard(request)
    if not isinstance(approve, bool) or not isinstance(proposal_id, str) or len(proposal_id) != 32:
        raise HTTPException(422, 'Valid approval decision required')
    with po_write_lock(request, platform), po_store._lock:
        path = _path(request, platform)
        rows = _reconcile(request, platform, _rows(path))
        p = next((x for x in rows if x.get('id') == proposal_id), None)
        if p is None:
            raise HTTPException(404, 'Receiving proposal not found')
        if p['state'] != 'pending':
            raise HTTPException(409, 'Receiving action is already decided or needs manual review')
        if not approve:
            p.update(state='rejected', decided_at=_now())
            po_store._write(path, rows)
            return {'state': 'rejected', 'executed': False, 'proposal_id': proposal_id}
        summary = review(request, p['po_id'], p['quantity'])
        if summary['previously_received'] != p['expected_received'] or summary['outstanding_quantity'] != p['expected_outstanding']:
            raise HTTPException(409, 'Purchase order receiving changed; create a fresh proposal')
        # A previously received slip cannot be replayed with a different approval ID.
        if any(e.get('po_id') == p['po_id'] and str(e.get('reference') or '').casefold() == p['reference'].casefold()
               for e in po_store._receive_events(request, platform)):
            raise HTTPException(409, 'Packing slip reference already received for this purchase order')
        p.update(state='executing', decided_at=_now())
        po_store._write(path, rows)
        try:
            # Use the established PO receiving endpoint, including its request-ID
            # idempotency and outstanding-quantity check. No on-hand stock change.
            result = po_store.receive_po(platform, p['po_id'], po_store.ReceiveInput(
                quantity=p['quantity'], reference=p['reference'], notes=p['notes'],
                to_inventory=False, request_id='moses-receive-' + proposal_id), request)
        except Exception:
            # If the write partially happened, reconciliation checks the journal;
            # never automatically retry after a possibly committed operation.
            _reconcile(request, platform, rows)
            raise
        p.update(state='executed', receipt_id=result['event']['id'], executed_at=_now())
        po_store._write(path, rows)
        return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                'receipt_id': result['event']['id'], 'outstanding': result['outstanding'],
                'inventory_changed': False, 'supplier_bill_created': False}
