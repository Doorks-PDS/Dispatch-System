"""Feature-gated, approval-controlled Doorks supplier bills.

Stores proposals separately, but posts an approved bill in the EXISTING
supplier_bills.json format. Does not send, pay, or change inventory. The durable
proposal ID is embedded in the bill for reconciliation after an uncertain write.
The feature stays OFF until existing non-Moses accounting writers are validated
for concurrent access across production workers.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException
from app.routers import doorks_accounting as accounting, doorks_workflow as workflow
from app.services.moses_supplier_bill_review import review, _money


def now():
    return datetime.now(timezone.utc).isoformat()


def guard(request):
    if request.session.get('active_platform') != 'doorks' or not getattr(request.state, 'auth_user', None) or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Doorks office admin required')
    if os.getenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED', '').strip().lower() != 'true':
        raise HTTPException(503, 'Supplier bill actions disabled until concurrency verification')


def path(request):
    return accounting.base(request) / 'moses_supplier_bill_proposals.json'


def records(request):
    return accounting.base(request) / 'supplier_bills.json'


def proposals(request):
    return accounting.read(path(request))


@contextmanager
def locked(request):
    # The normal Doorks supplier-bill editor and Moses both acquire this
    # filesystem lock BEFORE reading/updating supplier_bills.json.
    from app.services.doorks_supplier_bill_lock import supplier_bill_lock
    with supplier_bill_lock(request):
        yield


def _matching_bill(bills, p):
    return next((b for b in bills if b.get('moses_proposal_id') == p['id']), None)


def _reconcile(request, rows):
    bills = accounting.read(records(request))
    dirty = False
    for p in rows:
        if p.get('state') != 'executing':
            continue
        bill = _matching_bill(bills, p)
        p['state'] = 'executed' if bill else 'needs_review'
        p['reconciled_at'] = now()
        if bill:
            p['bill_id'] = bill['id']
        dirty = True
    if dirty:
        accounting.write(path(request), rows)
    return rows


def _safe_check(request, po_id, bill_number, amount):
    result = review(request, po_id, bill_number, float(amount))
    # Conservatively disallow partial receipts / missing total. User may still
    # enter these through the normal accounting editor with its own review.
    if result['received_quantity'] <= 0 or result['outstanding_quantity'] != 0:
        raise HTTPException(409, 'PO must be fully received before Moses can create a supplier bill')
    if result['po_total'] is None:
        raise HTTPException(409, 'PO needs an established total before Moses can create a supplier bill')
    if result['bill_already_exists']:
        raise HTTPException(409, 'Supplier bill number already linked to this PO')
    if any('Duplicate linked' in issue for issue in result['issues']):
        raise HTTPException(409, 'Duplicate supplier bills on PO require manual reconciliation')
    if Decimal(str(result['existing_billed_amount'])) + amount > Decimal(str(result['po_total'])):
        raise HTTPException(409, 'Supplier bills would exceed PO total')
    return result


def propose(request, po_identifier, bill_number, bill_amount, due_date=''):
    guard(request)
    if not isinstance(bill_number, str) or not 1 <= len(bill_number.strip()) <= 120:
        raise HTTPException(422, 'Supplier bill number required (up to 120 characters)')
    amount = _money(bill_amount, required=True)
    if amount <= 0:
        raise HTTPException(422, 'Supplier bill amount must be positive')
    if due_date:
        try:
            if not isinstance(due_date, str) or date.fromisoformat(due_date).isoformat() != due_date:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, 'Due date must be YYYY-MM-DD')
    with locked(request):
        check = _safe_check(request, po_identifier, bill_number.strip(), amount)
        rows = _reconcile(request, proposals(request))
        if any(p.get('state') in ('pending', 'executing', 'needs_review') and p['po_id'] == check['po_id'] and p['bill_number'].casefold() == bill_number.strip().casefold() for p in rows):
            raise HTTPException(409, 'Bill number already awaiting approval or review')
        p = dict(id=uuid.uuid4().hex, state='pending', platform='doorks',
                 po_id=check['po_id'], po_number=check['po_number'], supplier=check['supplier'],
                 bill_number=bill_number.strip(), amount=float(amount), due_date=due_date,
                 expected_billed=check['existing_billed_amount'],
                 expected_po_total=check['po_total'],
                 created_at=now(), requested_by=str(request.state.auth_user.get('id', 'office_admin'))[:100])
        rows.append(p)
        accounting.write(path(request), rows)
        return {'proposal': p, 'approval_required': True, 'executed': False, 'payment_recorded': False}


def pending(request):
    guard(request)
    with locked(request):
        rows = _reconcile(request, proposals(request))
        entries = [p for p in rows if p['state'] in ('pending', 'needs_review')]
        return {'proposals': entries, 'count': len(entries)}


def decide(request, proposal_id, approve):
    guard(request)
    if not isinstance(approve, bool) or not isinstance(proposal_id, str) or len(proposal_id) != 32:
        raise HTTPException(422, 'Valid decision and proposal ID required')
    with locked(request):
        rows = _reconcile(request, proposals(request))
        p = next((item for item in rows if item['id'] == proposal_id), None)
        if p is None:
            raise HTTPException(404, 'Proposal not found')
        if p['state'] != 'pending':
            raise HTTPException(409, 'Already decided or requires manual review')
        if not approve:
            p.update(state='rejected', decided_at=now())
            accounting.write(path(request), rows)
            return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False}
        amount = _money(p['amount'], required=True)
        current = _safe_check(request, p['po_id'], p['bill_number'], amount)
        if (Decimal(str(current['existing_billed_amount'])) != Decimal(str(p['expected_billed'])) or
            Decimal(str(current['po_total'])) != Decimal(str(p['expected_po_total']))):
            raise HTTPException(409, 'PO billing changed; prepare a new proposal')
        bills = accounting.read(records(request))
        supplier = str(p['supplier']).strip().casefold()
        if any(str(b.get('bill_number') or '').strip().casefold() == p['bill_number'].casefold() and
               str(b.get('vendor') or b.get('supplier') or '').strip().casefold() == supplier for b in bills):
            raise HTTPException(409, 'Supplier bill number already exists for this vendor')
        p.update(state='executing', decided_at=now())
        accounting.write(path(request), rows)
        record = dict(id=uuid.uuid4().hex, source_po_id=p['po_id'],
                      po_number=p['po_number'], vendor=p['supplier'], bill_number=p['bill_number'],
                      amount=p['amount'], paid=0, status='Open', due_date=p['due_date'],
                      moses_proposal_id=p['id'], created_at=now())
        try:
            bills.append(record)
            accounting.write(records(request), bills)
        except Exception:
            _reconcile(request, rows)
            raise
        p.update(state='executed', bill_id=record['id'], executed_at=now())
        accounting.write(path(request), rows)
        return {'proposal_id': proposal_id, 'bill_id': record['id'], 'state': 'executed',
                'executed': True, 'payment_recorded': False, 'inventory_changed': False}
