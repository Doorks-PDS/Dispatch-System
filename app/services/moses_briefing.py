"""Atlas/Moses verified read-only business briefing.

Uses *only* the current authorized workspace. No AI generation, action, disk
creation, financial posting, or external requests. Explicit field allowlist.
"""
from __future__ import annotations

import json
from pathlib import Path
from fastapi import HTTPException

_PDS_QUEUES = {
    'needs_quote': ('to be quoted', 'quote', 'complete/quote'),
    'needs_invoice': ('to be invoiced',),
    'parts_on_order': ('parts on order',),
    'in_progress': ('in progress',),
    'scheduled': ('scheduled',),
    'approved': ('approved',),
}
_WORK_QUEUES = {
    'needs_quote': ('to be quoted',),
    'needs_invoice': ('to be invoiced',),
    'parts_on_order': ('parts on order',),
    'in_progress': ('in progress',),
    'scheduled': ('scheduled',),
    'approved': ('approved',),
}
_TITLE = {
    'needs_quote': 'Jobs needing a quote',
    'needs_invoice': 'Jobs needing an invoice',
    'parts_on_order': 'Parts on order',
    'in_progress': 'Jobs in progress',
    'scheduled': 'Scheduled jobs',
    'approved': 'Approved work',
    'leads_new': 'New Atlas inquiries',
    'orders_open': 'Open SDC orders',
    'unpaid_invoices': 'Invoices requiring review',
    'po_open': 'Purchase orders requiring review',
}


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in to use Moses')
    platform = request.session.get('active_platform')
    if platform not in ('pds', 'doorks', 'sdc') or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active workspace office-admin access required')
    return platform


def _load_workspace(request, platform, kind):
    """Read an existing file; never create directories/files as a side effect."""
    base = Path(request.app.state.data_dir) / 'business_workspaces' / platform
    filename = base / (kind + '.json')
    if not filename.is_file():
        return None
    try:
        data = json.loads(filename.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise HTTPException(503, 'Saved workspace records could not be read') from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise HTTPException(503, 'Saved workspace record format is invalid')
    return data


def _safe_row(item, *, sdc=False):
    fields = ('id', 'job_number', 'order_number', 'customer', 'customer_name',
              'status', 'date', 'scheduled_date', 'document_number', 'po_number',
              'company', 'name') if sdc else (
              'id', 'job_number', 'customer', 'customer_name', 'status', 'date',
              'scheduled_date', 'po_number')
    return {key: str(item[key])[:120] for key in fields
            if isinstance(item.get(key), (str, int, float)) and not isinstance(item.get(key), bool)}


def _section(rows, statuses, *, sdc=False):
    selected = [row for row in rows if str(row.get('status') or '').strip().casefold() in statuses]
    # Full count, bounded examples, never expose free-form notes, emails or amounts.
    return {'count': len(selected), 'examples': [_safe_row(r, sdc=sdc) for r in selected[:4]]}


def brief(request):
    """Office-admin, active-workspace-only operational snapshot; never writes."""
    platform = _guard(request)
    if platform == 'pds':
        try:
            rows = request.app.state.calendar_store.list_jobs()
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise HTTPException(503, 'PDS CalendarStore currently unavailable') from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise HTTPException(503, 'PDS job records are unavailable')
        queues = {name: _section(rows, statuses) for name, statuses in _PDS_QUEUES.items()}
        return {'workspace': platform, 'read_only': True, 'source': 'PDS CalendarStore',
                'total_jobs': len(rows), 'queues': queues, 'records_changed': False}

    if platform == 'doorks':
        rows = _load_workspace(request, 'doorks', 'work_orders')
        if rows is None:
            raise HTTPException(503, 'Doorks work orders have not been verified')
        queues = {name: _section(rows, statuses) for name, statuses in _WORK_QUEUES.items()}
        po = _load_workspace(request, 'doorks', 'purchase_orders')
        if po is not None:
            queues['po_open'] = _section(po, {'draft', 'pending', 'ordered', 'open'}, sdc=True)
        return {'workspace': platform, 'read_only': True, 'source': 'Doorks business workspace',
                'total_jobs': len(rows), 'queues': queues, 'records_changed': False}

    # SDC's lead list is production business data; do not infer its sales revenue.
    leads = _load_workspace(request, 'sdc', 'software_leads')
    orders = _load_workspace(request, 'sdc', 'orders')
    documents = _load_workspace(request, 'sdc', 'estimates_invoices')
    if leads is None and orders is None and documents is None:
        raise HTTPException(503, 'SDC saved records are not available')
    queues = {}
    if leads is not None:
        queues['leads_new'] = _section(leads, {'new', 'pending', 'uncontacted'}, sdc=True)
    if orders is not None:
        queues['orders_open'] = _section(orders, {'open', 'in production', 'pending'}, sdc=True)
    if documents is not None:
        # Only invoice-type records; never mix unpaid quotes and invoices.
        invoices = [row for row in documents if str(row.get('document_type') or row.get('type') or '').casefold() == 'invoice']
        queues['unpaid_invoices'] = _section(invoices, {'draft', 'sent', 'overdue', 'unpaid', 'pending'}, sdc=True)
    return {'workspace': platform, 'read_only': True, 'source': 'SDC business workspace',
            'queues': queues, 'records_changed': False}


def summary(report):
    if not isinstance(report, dict) or not report.get('read_only'):
        raise ValueError('Only verified read-only briefings may be summarized')
    lines = [f"{report['workspace'].upper()} business briefing — saved records:"]
    for key, info in report['queues'].items():
        lines.append(f"{_TITLE.get(key, key)}: {info['count']}")
        for row in info['examples'][:4]:
            identifier = row.get('job_number') or row.get('order_number') or row.get('document_number') or row.get('po_number') or ''
            customer = row.get('customer') or row.get('customer_name') or row.get('company') or row.get('name') or ''
            title = ' | '.join(str(v)[:100] for v in (identifier, customer, row.get('status', '')) if v)
            if title:
                lines.append('  • ' + title)
    lines.append('This is a read-only overview. Nothing was updated, emailed, charged, or approved.')
    return '\n'.join(lines)
