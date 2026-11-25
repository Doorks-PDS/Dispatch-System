"""PDS supplier purchase order QuickBooks handoff; no external accounting writes.

Prepare-only queue, independent of customer PO numbers and invoice handoffs.
Office Admin only. POs are non-posting commitments, not vendor bills, payments,
or inventory movements. QB vendor/expense item matching is deferred to the adapter.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb

PO_RE = re.compile(r'PO-\d{5,}\Z', re.I)
CENT = Decimal('0.01')
MAX_ROWS = 10000
MAX_LINES = 100


def _path(request):
    return Path(request.app.state.data_dir) / 'pds_quickbooks_po_handoff.json'


def _source(request):
    path = Path(request.app.state.data_dir) / 'pds_purchase_orders' / 'records.json'
    if not path.is_file():
        return []
    try:
        orders = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Supplier PO register unreadable; office review required') from exc
    if not isinstance(orders, list) or len(orders) > MAX_ROWS or any(not isinstance(x, dict) for x in orders):
        raise HTTPException(503, 'Supplier PO register invalid; office review required')
    return orders


def _lines(po):
    value = po.get('line_items') or ''
    try:
        if isinstance(value, str):
            value = json.loads(value) if value.strip() else []
    except ValueError as exc:
        raise ValueError('PO line items need review') from exc
    if not isinstance(value, list) or not value or len(value) > MAX_LINES:
        raise ValueError('PO needs valid line items')
    subtotal = Decimal(0)
    for line in value:
        if not isinstance(line, dict) or not str(line.get('item') or line.get('description') or '').strip():
            raise ValueError('PO item or description missing')
        qty = qb._money(line.get('quantity'))
        rate = qb._money(line.get('rate'))
        if qty <= 0 or rate < 0:
            raise ValueError('Invalid supplier quantity or purchase cost')
        subtotal += qty * rate
    return subtotal.quantize(CENT, rounding=ROUND_HALF_UP), len(value)


def _job(po, jobs):
    job_id = str(po.get('job_id') or '').strip()
    number = str(po.get('work_order') or po.get('work_order_number') or '').strip()
    if not (job_id or number):
        return None
    matches = [x for x in jobs if isinstance(x, dict) and (
        str(x.get('id') or '') == job_id if job_id else
        str(x.get('job_number') or '').casefold() == number.casefold())]
    if len(matches) != 1:
        return None
    job = matches[0]
    if number and str(job.get('job_number') or '').casefold() != number.casefold():
        return None
    if po.get('customer') and str(job.get('customer') or '').strip().casefold() != str(po.get('customer') or '').strip().casefold():
        return None
    return job


def _row(po, jobs):
    number = str(po.get('po_number') or '').strip().upper()
    if not PO_RE.fullmatch(number):
        return None
    vendor = str(po.get('vendor') or '').strip()
    job = _job(po, jobs)
    source_id = str(po.get('id') or '').strip()
    status = str(po.get('status') or 'Draft').strip() or 'Draft'
    normalized = status.casefold().replace('_', ' ').replace('-', ' ')
    reasons = []
    if not source_id:
        reasons.append('Saved PO ID missing')
    if not vendor:
        reasons.append('Supplier is required')
    if not job:
        reasons.append('Job/customer linkage needs review (stock purchases can be handled later)')
    if normalized not in ('ordered', 'shipped', 'en route', 'delivered', 'received'):
        reasons.append('PO must be ordered or later; draft/cancelled POs are excluded')
    subtotal = tax = shipping = total = Decimal('0')
    count = 0
    try:
        subtotal, count = _lines(po)
        tax = qb._money(po.get('tax'))
        shipping = qb._money(po.get('shipping'))
        saved_total = qb._money(po.get('total'))
        total = (subtotal + tax + shipping).quantize(CENT, rounding=ROUND_HALF_UP)
        if tax < 0 or shipping < 0 or total <= 0:
            raise ValueError('PO costs, tax and shipping must be valid')
        if abs(saved_total - total) > CENT:
            raise ValueError('Saved PO total does not match supplier lines plus tax and shipping')
    except (ValueError, TypeError) as exc:
        reasons.append(str(exc))
    row = {
        'number': number, 'source_id': source_id, 'vendor': vendor,
        'supplier_id': str(po.get('supplier_id') or ''),
        'job_number': str(job.get('job_number') or '') if job else str(po.get('work_order') or po.get('work_order_number') or ''),
        'customer': str(po.get('customer') or ''), 'date': str(po.get('date') or ''),
        'order_status': status, 'line_count': count,
        'subtotal': f'{subtotal:.2f}', 'tax': f'{tax:.2f}',
        'shipping': f'{shipping:.2f}', 'total': f'{total:.2f}',
        'needs_review': reasons, 'ready': not reasons,
        'vendor_mapping_required': True,
        'note': 'QuickBooks vendor and item matching are required before any future live synchronization.',
    }
    # Fingerprint includes the complete source record so any later change to
    # vendor, quantities, shipping, status, tracking or job invalidates stage.
    source_digest = hashlib.sha256(json.dumps(po, sort_keys=True, default=str).encode()).hexdigest()
    row['fingerprint'] = hashlib.sha256(json.dumps({'row': row, 'source_digest': source_digest}, sort_keys=True).encode()).hexdigest()
    return row


def _rows(request):
    jobs = request.app.state.calendar_store.list_jobs()
    if not isinstance(jobs, list):
        raise HTTPException(503, 'Saved PDS jobs unavailable')
    rows = [_row(po, jobs) for po in _source(request)]
    # Duplicate supplier PO number is always an exception, not an arbitrary pick.
    numbers = [r['number'] for r in rows if r]
    if len(numbers) != len(set(numbers)):
        raise HTTPException(409, 'Duplicate supplier PO numbers require office reconciliation')
    return {r['number']: r for r in rows if r is not None}


def preview(request):
    qb._admin(request)
    rows = _rows(request)
    ledger = qb._load(_path(request))['items']
    for number, row in rows.items():
        item = ledger.get(number)
        state = item.get('state') if isinstance(item, dict) else None
        if item and item.get('fingerprint') != row['fingerprint']:
            state = 'changed_since_preparation'
            if 'Previously prepared PO changed; reconcile the handoff' not in row['needs_review']:
                row['needs_review'].append('Previously prepared PO changed; reconcile the handoff')
            row['ready'] = False
        row['handoff_status'] = state or 'not_prepared'
        row['prepared_at'] = item.get('prepared_at') if isinstance(item, dict) else None
    return {'purchase_orders': sorted(rows.values(), key=lambda r: r['number'], reverse=True),
            'ready_count': sum(r['ready'] and r['handoff_status'] == 'not_prepared' for r in rows.values()),
            'prepared_count': sum(r['handoff_status'] == 'prepared_for_review' for r in rows.values()),
            'connected_to_quickbooks': False, 'automatic_sync_enabled': False}


def prepare(request, number, fingerprint):
    qb._admin(request, mutation=True)
    number = str(number or '').upper()
    if not PO_RE.fullmatch(number) or not re.fullmatch('[a-f0-9]{64}', str(fingerprint or '')):
        raise HTTPException(422, 'Exact saved supplier PO and review fingerprint required')
    current = _rows(request).get(number)
    if current is None:
        raise HTTPException(404, 'Saved supplier PO not found')
    path = _path(request)
    with qb._lock(path):
        ledger = qb._load(path)
        existing = ledger['items'].get(number)
        if existing:
            if existing.get('fingerprint') != current['fingerprint']:
                raise HTTPException(409, 'Previously prepared PO changed; reconcile the existing handoff')
            return {'number': number, 'state': existing['state'], 'duplicate': True, 'pushed_to_quickbooks': False}
        if not current['ready']:
            raise HTTPException(409, '; '.join(current['needs_review']))
        if fingerprint != current['fingerprint']:
            raise HTTPException(409, 'PO changed since preview; refresh before preparing')
        actor = getattr(request.state, 'auth_user', {}) or {}
        ledger['items'][number] = {
            'state': 'prepared_for_review', 'fingerprint': fingerprint,
            'source_id': current['source_id'], 'job_number': current['job_number'],
            'vendor': current['vendor'], 'total': current['total'],
            'prepared_at': datetime.now(timezone.utc).isoformat(),
            'prepared_by': str(actor.get('id') or '')[:120],
        }
        qb._save(path, ledger)
    return {'number': number, 'state': 'prepared_for_review', 'duplicate': False, 'pushed_to_quickbooks': False}


def export_review_csv(request):
    qb._admin(request)
    rows = _rows(request)
    ledger = qb._load(_path(request))['items']
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['PDS Supplier PO', 'Supplier', 'PDS Job #', 'Customer', 'Date',
                     'Order Status', 'Line Count', 'Subtotal', 'Tax Amount', 'Shipping',
                     'PO Total', 'QuickBooks Handoff State', 'QuickBooks Vendor Mapping'])
    for number in sorted(ledger):
        item = ledger[number]
        row = rows.get(number)
        if not isinstance(item, dict) or row is None or item.get('fingerprint') != row['fingerprint']:
            continue
        writer.writerow([qb._excel_safe(row['number']), qb._excel_safe(row['vendor']),
                         qb._excel_safe(row['job_number']), qb._excel_safe(row['customer']),
                         qb._excel_safe(row['date']), qb._excel_safe(row['order_status']),
                         row['line_count'], row['subtotal'], row['tax'], row['shipping'], row['total'],
                         'Prepared for review (not synced)', 'Not connected'])
    return out.getvalue()
