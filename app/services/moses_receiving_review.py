"""Read-only purchase-order / packing-slip reconciliation for Moses.

Uses the pre-existing PDS PO and per-workspace append-only receiving journal.
Never creates receipts, modifies inventory, or processes supplier bills.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from app.routers import pds_purchase_orders as po_store


def _qty(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(409, 'Purchase order or receiving journal has invalid quantity')
    if not number.is_finite() or number < 0:
        raise HTTPException(409, 'Purchase order or receiving journal has invalid quantity')
    return number


def review(request, po_identifier: str, packing_slip_quantity: float | None = None) -> dict:
    """Compare a confirmed packing-slip quantity with a single saved PO; no writes."""
    platform = request.session.get('active_platform')
    if platform not in ('pds', 'doorks', 'sdc'):
        raise HTTPException(403, 'Unsupported workspace')
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office Admin only')
    if not isinstance(po_identifier, str) or not 1 <= len(po_identifier.strip()) <= 100:
        raise HTTPException(422, 'Exact PO number or ID required')
    requested = po_identifier.strip().casefold()
    incoming = None
    if packing_slip_quantity is not None:
        incoming = _qty(packing_slip_quantity)
        if incoming <= 0 or incoming > 1000000:
            raise HTTPException(422, 'Packing slip quantity must be positive and at most 1000000')
    # Reuse established workspace authorization and shared receiving lock.
    orders_path = po_store._receive_context(request, platform)
    with po_store._lock:
        orders = po_store._read(orders_path, [])
        matches = [item for item in orders if isinstance(item, dict) and
                   (str(item.get('id', '')).casefold() == requested or
                    str(item.get('po_number', '')).casefold() == requested)]
        if len(matches) != 1:
            raise HTTPException(404 if not matches else 409,
                                'Purchase order not found' if not matches else 'Ambiguous purchase order')
        order = matches[0]
        if platform == 'doorks':
            legacy = _qty(order.get('received_quantity') or 0)
            if legacy > 0:
                raise HTTPException(409, 'Legacy receiving quantity exists; manual reconciliation required before Moses receiving')
        if str(order.get('status', '')).strip().casefold() in ('cancelled', 'canceled'):
            raise HTTPException(409, 'Cancelled purchase order cannot be received')
        ordered = _qty(order.get('quantity') or 0)
        if ordered <= 0:
            raise HTTPException(409, 'PO does not have a valid ordered quantity')
        events = po_store._receive_events(request, platform)
        received = sum((_qty(event.get('quantity')) for event in events
                        if event.get('po_id') == str(order.get('id'))), Decimal(0))
    remaining = ordered - received
    if remaining < 0:
        raise HTTPException(409, 'Receiving journal exceeds ordered quantity; manual review required')
    # Exclude internal notes, employee IDs, private documents, and the raw journal.
    report = {'workspace': platform, 'po_id': str(order.get('id', '')),
              'po_number': str(order.get('po_number') or ''),
              'supplier': str(order.get('vendor') or order.get('supplier') or '')[:160],
              'ordered_quantity': float(ordered), 'previously_received': float(received),
              'outstanding_quantity': float(remaining),
              'read_only': True, 'receipt_posted': False, 'inventory_changed': False}
    if incoming is not None:
        report.update({'packing_slip_quantity': float(incoming),
                       'quantity_matches_outstanding': incoming == remaining,
                       'over_receipt': incoming > remaining,
                       'short_receipt': incoming < remaining,
                       'requires_review': incoming != remaining,
                       'next_step': ('Review discrepancy before any receipt is posted' if incoming != remaining
                                     else 'Quantity agrees; request separate approval before posting receipt')})
    return report
