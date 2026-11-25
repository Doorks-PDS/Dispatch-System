"""PDS QuickBooks invoice handoff -- read-only preview and explicit staging.

This is NOT a QuickBooks connector, invoice creation, or payment posting. It is
an edition-neutral, idempotent queue for a later QBO or Desktop adapter. Only
confirmed *issued* PDS invoices enter the queue; saved PDFs alone do not qualify.
No estimates, customer PO numbers, supplier POs, payments or stock are changed.
"""
from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from fastapi import HTTPException

INVOICE_RE = re.compile(r"JS\d{5,}\Z", re.I)
MONEY = Decimal('0.01')
MAX_INVOICES = 100


def _admin(request, *, mutation=False):
    # Every QuickBooks endpoint (including previews and CSV) is administrator only.
    if (not getattr(request.state, 'auth_user', None)
            or request.session.get('active_platform') != 'pds'
            or getattr(request.state, 'auth_role', '') != 'office_admin'):
        raise HTTPException(403, 'PDS Office Admin access required')


def _settings_path(request):
    return Path(request.app.state.data_dir) / 'pds_quickbooks_settings.json'


def _mode(request):
    # The environment setting, if present, takes priority over the saved choice.
    value = os.getenv('PDS_QUICKBOOKS_EDITION', '').strip().lower()
    if value in ('online', 'desktop'):
        return value
    path = _settings_path(request)
    if not path.exists():
        return 'not_selected'
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'QuickBooks setup needs administrator review') from exc
    if not isinstance(record, dict) or record.get('edition') not in ('online', 'desktop', 'not_selected'):
        raise HTTPException(503, 'QuickBooks setup needs administrator review')
    return record['edition']


def select_edition(request, edition):
    _admin(request)
    if edition not in ('online', 'desktop', 'not_selected'):
        raise HTTPException(422, 'Select Online or Desktop')
    if os.getenv('PDS_QUICKBOOKS_EDITION', '').strip().lower() in ('online', 'desktop'):
        raise HTTPException(409, 'Edition is managed in Render settings')
    path = _settings_path(request)
    with _lock(path):
        _save(path, {'edition': edition, 'updated_at': datetime.now(timezone.utc).isoformat(),
                     'updated_by': str((request.state.auth_user or {}).get('id') or '')[:120]})
    return status(request)


def _ledger_path(request):
    return Path(request.app.state.data_dir) / 'pds_quickbooks_invoice_handoff.json'


@contextmanager
def _lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a+b') as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _load(path):
    if not path.exists():
        return {'version': 1, 'items': {}}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'QuickBooks handoff ledger needs office review') from exc
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('items'), dict):
        raise HTTPException(503, 'QuickBooks handoff ledger needs office review')
    return value


def _save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.qb-handoff-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _money(value):
    try:
        number = Decimal(str(value if value is not None else '0'))
        if not number.is_finite() or abs(number) > Decimal('10000000'):
            raise ValueError('Invalid amount')
        return number
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise ValueError('Invalid amount') from exc


def _invoice_snapshots_sent(request):
    """Only Resend-accepted invoice actions. Never imply inbox delivery."""
    path = Path(request.app.state.data_dir) / 'moses_pds_document_delivery_actions.json'
    if not path.exists():
        return {}
    try:
        actions = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Invoice delivery ledger unreadable') from exc
    if not isinstance(actions, list):
        raise HTTPException(503, 'Invoice delivery ledger invalid')
    snapshots = {}
    for row in actions:
        if not isinstance(row, dict) or row.get('state') != 'sent':
            continue
        snap = row.get('snapshot')
        if not isinstance(snap, dict) or snap.get('kind') != 'invoice':
            continue
        number = str(snap.get('number') or '').upper()
        if INVOICE_RE.fullmatch(number):
            snapshots.setdefault(number, []).append(snap)
    return snapshots


def _row(request, doc, jobs, issued):
    number = str(doc.get('number') or '').upper()
    if not INVOICE_RE.fullmatch(number) or doc.get('type') != 'invoice':
        return None
    job_id = str(doc.get('job_id') or '').strip()
    job_number = str(doc.get('job_number') or '').strip()
    matches = [j for j in jobs if isinstance(j, dict) and (
        (job_id and str(j.get('id') or '') == job_id) or
        (not job_id and job_number and str(j.get('job_number') or '').casefold() == job_number.casefold()))]
    valid_job = (len(matches) == 1 and (not job_number or str(matches[0].get('job_number') or '').casefold() == job_number.casefold())
                 and str(matches[0].get('customer') or '').strip().casefold() == str(doc.get('customer') or '').strip().casefold())
    pdf_dir = request.app.state.documents_store.dir
    path = pdf_dir / (number + '.pdf')
    raw_pdf = b''
    if (not doc.get('_read_only_pdf_fallback') and str(doc.get('filename') or '') == path.name
            and path.is_file() and 5 < path.stat().st_size <= 10 * 1024 * 1024):
        raw_pdf = path.read_bytes()
    valid_pdf = raw_pdf.startswith(b'%PDF')
    pdf_hash = hashlib.sha256(raw_pdf).hexdigest() if valid_pdf else ''
    # Only the exact previously accepted PDF, not an older version of this
    # invoice number, can be queued for accounting. Check the linked job too.
    issued_exact = bool(valid_pdf and any(
        str(snap.get('pdf_sha256') or '') == pdf_hash
        and str(snap.get('job_id') or '') == job_id
        and str(snap.get('job_number') or '').casefold() == job_number.casefold()
        for snap in issued.get(number, ())))
    lines = doc.get('items') or []
    subtotal = Decimal('0')
    taxable = Decimal('0')
    error = ''
    try:
        if not isinstance(lines, list) or not lines:
            raise ValueError('No priced invoice items')
        if len(lines) > 150:
            raise ValueError('Too many invoice items')
        for item in lines:
            if not isinstance(item, dict):
                raise ValueError('Invalid invoice line')
            quantity, rate = _money(item.get('qty')), _money(item.get('rate'))
            if quantity <= 0 or rate < 0:
                raise ValueError('Invalid invoice quantity or price')
            amount = quantity * rate
            subtotal += amount
            if bool(item.get('taxable', True)):
                taxable += amount
        rate = _money(doc.get('tax_rate'))
        if not 0 <= rate <= 15:
            raise ValueError('Tax rate needs review')
        tax = (taxable * rate / 100).quantize(MONEY, rounding=ROUND_HALF_UP)
        total = subtotal.quantize(MONEY, rounding=ROUND_HALF_UP) + tax
        if total <= 0:
            raise ValueError('No positive invoice total')
    except (ValueError, InvalidOperation) as exc:
        error = str(exc)
        subtotal = tax = total = Decimal('0')
    reasons = []
    if not valid_job:
        reasons.append('Job/customer linkage needs review')
    if not valid_pdf:
        reasons.append('Saved PDF is missing or not verified')
    if not issued_exact:
        reasons.append('Current PDF not confirmed accepted by Resend')
    if error:
        reasons.append(error)
    payload = {'number': number, 'job_number': str(matches[0].get('job_number') or '') if valid_job else job_number,
               'customer': str(doc.get('customer') or ''), 'date': str(doc.get('date') or ''),
               'subtotal': f'{subtotal:.2f}', 'tax': f'{tax:.2f}', 'total': f'{total:.2f}',
               'terms': str(doc.get('terms') or ''), 'pdf_verified': valid_pdf,
               'resend_accepted': issued_exact, 'ready': not reasons, 'needs_review': reasons,
               'invoice_created_at': str(doc.get('created_at') or '')}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    payload['fingerprint'] = fingerprint
    return payload


def _rows(request):
    docs = request.app.state.documents_store.list_documents()
    jobs = request.app.state.calendar_store.list_jobs()
    if not isinstance(docs, list) or not isinstance(jobs, list):
        raise HTTPException(503, 'PDS document or job store unavailable')
    issued = _invoice_snapshots_sent(request)
    rows = [_row(request, d, jobs, issued) for d in docs if isinstance(d, dict)]
    return {r['number']: r for r in rows if r is not None}


def status(request):
    _admin(request)
    p = _ledger_path(request)
    ledger = _load(p)
    return {'edition': _mode(request), 'connected_to_quickbooks': False,
            'automatic_sync_enabled': False, 'invoices_only': True,
            'prepared_count': len(ledger['items']),
            'payments_modified': False, 'inventory_modified': False,
            'note': 'Invoice handoff prepared locally. Live QuickBooks sync requires the correct Online or Desktop adapter and one-time account authorization.'}


def preview(request):
    _admin(request)
    rows = _rows(request)
    ledger = _load(_ledger_path(request))['items']
    for number, row in rows.items():
        item = ledger.get(number)
        state = (item.get('state') if isinstance(item, dict) else 'not_prepared')
        if isinstance(item, dict) and item.get('fingerprint') != row['fingerprint']:
            state = 'changed_since_preparation'
            row['ready'] = False
            row['needs_review'].append('Previously prepared invoice changed; reconcile the handoff')
        row['handoff_status'] = state
        row['prepared_at'] = (item.get('prepared_at') if isinstance(item, dict) else None)
    return {'invoices': sorted(rows.values(), key=lambda r:r['number'], reverse=True),
            'ready_count': sum(bool(r['ready']) for r in rows.values()), 'edition': _mode(request)}


def prepare(request, number, fingerprint):
    _admin(request, mutation=True)
    if not INVOICE_RE.fullmatch(number or '') or len(fingerprint or '') != 64:
        raise HTTPException(422, 'Exact saved invoice and review fingerprint required')
    rows = _rows(request)
    current = rows.get(number.upper())
    if not current:
        raise HTTPException(404, 'Saved PDS invoice not found')
    if not current['ready']:
        raise HTTPException(409, '; '.join(current['needs_review']))
    if current['fingerprint'] != fingerprint:
        raise HTTPException(409, 'Invoice changed since preview; refresh before preparing')
    path = _ledger_path(request)
    with _lock(path):
        ledger = _load(path)
        existing = ledger['items'].get(current['number'])
        if existing:
            if existing.get('fingerprint') != fingerprint:
                raise HTTPException(409, 'Previously prepared invoice changed; reconcile the existing handoff')
            return {'number': current['number'], 'state': existing['state'], 'duplicate': True,
                    'pushed_to_quickbooks': False}
        now = datetime.now(timezone.utc).isoformat()
        who = getattr(request.state, 'auth_user', {}) or {}
        ledger['items'][current['number']] = {'state': 'prepared_for_review', 'fingerprint': fingerprint,
                                               'prepared_at': now, 'prepared_by': str(who.get('id') or '')[:120]}
        _save(path, ledger)
    return {'number': current['number'], 'state': 'prepared_for_review', 'duplicate': False,
            'pushed_to_quickbooks': False}


def _excel_safe(value):
    s = str(value or '')
    # No cell from a customer or imported document can be evaluated as a formula.
    return "'" + s if s.startswith(('=', '+', '-', '@', '\t', '\r')) else s


def export_review_csv(request):
    _admin(request)
    rows = _rows(request)
    ledger = _load(_ledger_path(request))['items']
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['PDS Invoice', 'Customer', 'Job #', 'Date', 'Subtotal', 'Tax',
                     'Total', 'Terms', 'QuickBooks Handoff State'])
    for number in sorted(ledger):
        item = ledger[number]
        row = rows.get(number)
        if not row or not isinstance(item, dict) or item.get('fingerprint') != row['fingerprint']:
            continue
        writer.writerow([_excel_safe(row['number']), _excel_safe(row['customer']),
                         _excel_safe(row['job_number']), _excel_safe(row['date']),
                         row['subtotal'], row['tax'], row['total'],
                         _excel_safe(row['terms']), item.get('state', '')])
    return out.getvalue()
