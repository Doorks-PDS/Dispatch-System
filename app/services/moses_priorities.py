"""Moses verified, read-only next-work recommendations.

No guessed financial figures, no model writes, and no background automation.
Every list is scoped by the current authenticated workspace and built fresh.
"""
from __future__ import annotations

from datetime import date, datetime
from fastapi import HTTPException
from app.services.moses_briefing import _guard, _load_workspace, _safe_row

# Ordering is a *workflow* heuristic, not a claim of revenue or business urgency.
RULES = {
    'pds': (
        ('needs_quote', {'to be quoted', 'quote', 'complete/quote'}, 'Review the saved job and prepare an estimate for approval', 0),
        ('needs_invoice', {'to be invoiced'}, 'Review completed work and prepare an invoice', 1),
        ('parts_on_order', {'parts on order'}, 'Check delivery and the next scheduled visit', 2),
        ('scheduled', {'scheduled'}, 'Confirm staffing and appointment details', 3),
    ),
    'doorks': (
        ('needs_quote', {'to be quoted'}, 'Review the ticket and prepare an estimate draft', 0),
        ('needs_invoice', {'to be invoiced'}, 'Review saved estimate and invoice requirements', 1),
        ('parts_on_order', {'parts on order'}, 'Check purchasing and receiving', 2),
        ('scheduled', {'scheduled'}, 'Review assignment and scheduling', 3),
    ),
    'sdc': (
        ('leads_new', {'new', 'pending', 'uncontacted'}, 'Review lead and prepare a follow-up', 0),
        ('orders_open', {'open', 'in production', 'pending'}, 'Check order milestones and next customer update', 1),
        ('unpaid_invoices', {'draft', 'sent', 'overdue', 'unpaid', 'pending'}, 'Review invoice and payment status', 2),
    ),
}


def _rows(request, platform):
    if platform == 'pds':
        try:
            rows = request.app.state.calendar_store.list_jobs()
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise HTTPException(503, 'PDS CalendarStore unavailable') from exc
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise HTTPException(503, 'PDS job records unavailable')
        return {'jobs': rows}
    sources = ('work_orders',) if platform == 'doorks' else ('software_leads', 'orders', 'estimates_invoices')
    data = {kind: _load_workspace(request, platform, kind) for kind in sources}
    if all(value is None for value in data.values()):
        raise HTTPException(503, 'No saved workspace records available')
    return data


def _date_value(record):
    # Date is only for display/order; never claim an unverified SLA or deadline.
    raw = str(record.get('scheduled_date') or record.get('date') or '')[:10]
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return ''


def priorities(request, limit=12):
    platform = _guard(request)
    if not isinstance(limit, int) or not 1 <= limit <= 25:
        raise HTTPException(422, 'Limit must be 1 through 25')
    sources = _rows(request, platform)
    report = []
    counts = {}
    for queue, statuses, suggestion, rank in RULES[platform]:
        source = ('jobs' if platform == 'pds' else 'work_orders' if platform == 'doorks' else
                  'software_leads' if queue == 'leads_new' else 'orders' if queue == 'orders_open' else 'estimates_invoices')
        rows = sources.get(source)
        if rows is None:
            counts[queue] = None  # Missing collection is unknown, not zero.
            continue
        candidates = [r for r in rows if str(r.get('status') or '').strip().casefold() in statuses]
        if queue == 'unpaid_invoices':
            candidates = [r for r in candidates if str(r.get('document_type') or r.get('type') or '').casefold() == 'invoice']
        counts[queue] = len(candidates)
        for row in candidates:
            sanitized = _safe_row(row, sdc=(platform == 'sdc'))
            when = _date_value(row)
            if when:
                sanitized['date'] = when
            report.append({'queue': queue, 'record': sanitized, 'suggestion': suggestion,
                           '_rank': rank, '_date': when or '9999-12-31'})
    report.sort(key=lambda r: (r['_rank'], r['_date'], r['record'].get('id', '')))
    top = [{k: v for k, v in r.items() if not k.startswith('_')} for r in report[:limit]]
    return {'workspace': platform, 'read_only': True, 'verified': True,
            'source': 'current saved workspace records', 'counts': counts,
            'priorities': top, 'total_matched': len(report), 'limited_to': limit,
            'records_changed': False, 'executed': False,
            'note': 'Suggested review order, not an inferred deadline or confirmed urgency. Approval is required for any record change.'}


def summary(report):
    if not isinstance(report, dict) or report.get('verified') is not True or report.get('read_only') is not True:
        raise ValueError('A verified read-only priority report is required')
    lines = [report['workspace'].upper() + ' — suggested work priorities (saved records):']
    for queue, count in report['counts'].items():
        lines.append(f'{queue.replace("_", " ").title()}: {count if count is not None else "records unavailable"}')
    if not report['priorities']:
        lines.append('No matching records in the available work queues. This is not a guarantee that all work is complete.')
    for i, item in enumerate(report['priorities'][:8], 1):
        row = item['record']
        identity = row.get('job_number') or row.get('order_number') or row.get('document_number') or row.get('id', '')
        customer = row.get('customer') or row.get('customer_name') or row.get('company') or row.get('name', '')
        lines.append(f'{i}. {identity} | {customer} | {row.get("status", "")} — {item["suggestion"]}')
    lines.append('These are review suggestions only. I have not updated, approved, sent, or charged anything.')
    return '\n'.join(lines)
