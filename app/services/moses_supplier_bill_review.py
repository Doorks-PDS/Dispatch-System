"""Read-only Doorks PO / receiving / supplier-bill reconciliation.

Never adds a bill, records a payment, or assumes goods receipt means an
invoice has been received. PDS/SDC billing integration is not enabled.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from app.routers import pds_purchase_orders as po_store, doorks_accounting as accounting
from app.services.moses_receiving_review import review as receiving_review


def _money(value, *, required=False):
    if isinstance(value, bool):
        raise HTTPException(422, 'Invalid monetary amount')
    if value is None or value == '':
        if not required:
            return None
        raise HTTPException(422, 'Valid supplier bill amount required')
    try:
        n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(422, 'Invalid monetary amount')
    if not n.is_finite() or n < 0 or n > Decimal('999999999') or n.as_tuple().exponent < -2:
        raise HTTPException(422, 'Amount must be a nonnegative finite value in cents')
    return n.quantize(Decimal('.01'))


def review(request, po_identifier: str, bill_number: str = '', bill_amount: float | None = None) -> dict:
    if request.session.get('active_platform') != 'doorks' or getattr(request.state, 'auth_role', None) != 'office_admin' or not getattr(request.state, 'auth_user', None):
        raise HTTPException(403, 'Doorks workspace office admin required')
    if not isinstance(bill_number, str) or len(bill_number) > 120:
        raise HTTPException(422, 'Invalid bill number')
    amount = _money(bill_amount) if bill_amount is not None else None
    summary = receiving_review(request, po_identifier)
    po_id = summary['po_id']
    path = po_store._receive_context(request, 'doorks')
    with po_store._lock:
        orders = po_store._read(path, [])
        order = next((o for o in orders if isinstance(o, dict) and str(o.get('id')) == po_id), None)
        if order is None:
            raise HTTPException(409, 'Purchase order changed during review')
        bills = accounting.read(accounting.base(request, create=False) / 'supplier_bills.json')
    linked = [b for b in bills if isinstance(b, dict) and str(b.get('source_po_id') or '') == po_id]
    reference = bill_number.strip().casefold()
    matching = [b for b in linked if reference and str(b.get('bill_number') or '').strip().casefold() == reference]
    duplicates = sorted({str(b.get('bill_number') or '') for b in linked if
                         sum(str(other.get('bill_number') or '').strip().casefold() == str(b.get('bill_number') or '').strip().casefold()
                             for other in linked) > 1 and str(b.get('bill_number') or '').strip()})
    po_total = _money(order.get('total'))
    if po_total is None:
        quantity, unit = _money(order.get('quantity')), _money(order.get('unit_cost'))
        # Do not infer tax or freight: a quantity*unit-cost subtotal is not the PO total.
        subtotal = quantity * unit if quantity is not None and unit is not None else None
    else:
        subtotal = None
    total_billed = sum((_money(b.get('amount'), required=True) for b in linked), Decimal('0.00'))
    issues = []
    if summary['previously_received'] == 0:
        issues.append('No goods receipts recorded against this PO')
    if summary['outstanding_quantity'] > 0:
        issues.append('PO is not fully received; partial billing may be valid, review required')
    if matching:
        issues.append('Supplier bill number already exists for this PO')
    if duplicates:
        issues.append('Duplicate linked supplier bill numbers need review')
    if amount is not None and po_total is not None and total_billed + amount > po_total:
        issues.append('Proposed bill plus previously linked bills exceeds PO total')
    if po_total is None:
        issues.append('PO total not established; cannot verify billed amount')
    return {
        'workspace': 'doorks', 'po_id': po_id, 'po_number': summary['po_number'],
        'supplier': summary['supplier'], 'ordered_quantity': summary['ordered_quantity'],
        'received_quantity': summary['previously_received'],
        'outstanding_quantity': summary['outstanding_quantity'],
        'po_total': float(po_total) if po_total is not None else None,
        'po_subtotal_only': float(subtotal) if subtotal is not None else None,
        'existing_bill_count': len(linked), 'existing_billed_amount': float(total_billed),
        'bill_number': bill_number.strip(), 'bill_already_exists': bool(matching),
        'proposed_bill_amount': float(amount) if amount is not None else None,
        'requires_review': bool(issues), 'issues': issues,
        'read_only': True, 'bill_created': False, 'payment_recorded': False,
        'note': 'A receiving record is not proof of supplier invoicing, and a bill is not proof of payment.'
    }
