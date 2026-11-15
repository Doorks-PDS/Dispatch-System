"""Doorks-only read-only supplier payment audit.

Workflow events are NOT bank evidence; an interrupted manual write can leave
an event without its corresponding balance update. Never auto-post or auto-pay.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from fastapi import HTTPException
from app.routers import doorks_accounting as accounting


def _money(value):
    if isinstance(value, bool):
        raise HTTPException(409, 'Unreliable accounting amount requires review')
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('999999999') or amount != amount.quantize(Decimal('.01')):
            raise ValueError()
        return amount
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(409, 'Unreliable accounting amount requires review')


def _fmt(value):
    return format(value.quantize(Decimal('.01')), '.2f')


def review(request, bill_identifier: str):
    if (request.session.get('active_platform') != 'doorks' or
            getattr(request.state, 'auth_role', None) != 'office_admin' or
            not getattr(request.state, 'auth_user', None)):
        raise HTTPException(403, 'Doorks office admin required')
    if not isinstance(bill_identifier, str) or not bill_identifier.strip() or len(bill_identifier) > 120:
        raise HTTPException(422, 'Exact supplier bill ID or number required')
    # An absent accounting workspace is not a reason for a read-only audit to
    # create folders or a lock file. Writes remain protected by the shared lock.
    existing = accounting.base(request, create=False)
    if not existing.is_dir():
        raise HTTPException(404, 'Supplier bill not found')
    from app.services.doorks_supplier_bill_lock import supplier_bill_lock
    # Take a consistent snapshot relative to manual and Moses supplier writes.
    with supplier_bill_lock(request):
        folder = accounting.base(request)
        bills = accounting.read(folder / 'supplier_bills.json')
        events = accounting.read(folder / 'workflow_events.json')
    key = bill_identifier.strip().casefold()
    # Exact IDs take precedence; an ambiguous bill number is never guessed.
    matches = [b for b in bills if str(b.get('id', '')).strip() == bill_identifier.strip()]
    if not matches:
        matches = [b for b in bills if str(b.get('bill_number', '')).strip().casefold() == key]
    if not matches:
        raise HTTPException(404, 'Supplier bill not found')
    if len(matches) != 1:
        raise HTTPException(409, 'Ambiguous bill number; use exact internal bill ID')
    bill = matches[0]
    bill_id = str(bill.get('id', ''))
    if not bill_id:
        raise HTTPException(409, 'Bill has no stable ID; manual review required')
    total, paid = _money(bill.get('amount', 0)), _money(bill.get('paid', 0))
    payments = [e for e in events if e.get('kind') == 'supplier_bill' and
                str(e.get('source_id', '')) == bill_id and e.get('action') == 'payment_sent']
    event_sum = sum((_money(e.get('amount', 0)) for e in payments), Decimal('0'))
    issues = []
    if paid > total: issues.append('Recorded paid balance exceeds supplier bill amount')
    if event_sum != paid: issues.append('Payment audit events and recorded paid balance differ; review interrupted or older writes')
    if paid and not payments: issues.append('Paid amount has no matching workflow payment events')
    event_ids = [str(e.get('id') or '') for e in payments]
    if not all(event_ids) or len(set(event_ids)) != len(event_ids):
        issues.append('Missing or duplicate payment event identifiers')
    refs = [str(e.get('reference') or '').strip().casefold() for e in payments]
    nonempty = [r for r in refs if r]
    if len(nonempty) != len(set(nonempty)):
        issues.append('Repeated payment reference; investigate before recording another payment')
    if any(not r for r in refs):
        issues.append('One or more payment events lack a reference')
    if (paid >= total and str(bill.get('status', '')).casefold() != 'paid' and total > 0) or (paid < total and str(bill.get('status', '')).casefold() == 'paid'):
        issues.append('Bill status conflicts with recorded paid amount')
    return {
        'workspace':'doorks', 'bill_id':bill_id,
        'bill_number':str(bill.get('bill_number') or '')[:120],
        'supplier':str(bill.get('vendor') or bill.get('supplier') or '')[:120],
        'bill_amount':_fmt(total), 'recorded_paid':_fmt(paid),
        'remaining_balance':_fmt(max(Decimal('0'), total - paid)),
        'payment_event_count':len(payments), 'payment_event_total':_fmt(event_sum),
        'issues':issues, 'requires_manual_review':bool(issues),
        'external_payment_verified':False, 'bank_reconciled':False,
        'payment_executed':False,
        'note':'Read-only record comparison. Neither a workflow event nor a Paid status proves funds cleared the bank.'
    }
