"""Read-only Moses follow-through desk from verified existing business records.

No business writes, provider calls, automatic retry, or separate queue database.
Only the current office-admin workspace is visible. Missing sources stay unknown.
"""
from __future__ import annotations

from pathlib import Path
from fastapi import HTTPException

PDS_WORK = {
    'needs_quote': {'quote', 'complete/quote', 'to be quoted'},
    'needs_invoice': {'to be invoiced'},
    'parts_on_order': {'parts on order'},
}
DELIVERY_PROBLEMS = {
    'bounced': 'Email bounced',
    'failed': 'Email failed',
    'spam_complaint': 'Spam complaint',
    'suppressed': 'Email suppressed',
    'delivery_delayed': 'Delivery delayed',
}
KINDS = {'pds': ('dispatch',),
         'doorks': ('estimate', 'invoice', 'purchase_order'),
         'sdc': ('estimate', 'invoice', 'purchase_order')}


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    workspace = request.session.get('active_platform')
    if workspace not in KINDS or (getattr(request.state, 'auth_role', None) != 'office_admin' and not (workspace == 'pds' and getattr(request.state, 'auth_role', None) in ('office','lead'))):
        raise HTTPException(403, 'Active workspace office administrator required')
    return workspace


def _read_existing(path: Path):
    """None = no source; malformed existing records must never become an empty queue."""
    if not path.is_file():
        return None
    from app.routers.workspaces import load
    try:
        rows = load(path)
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'A saved follow-through source is unreadable') from exc
    if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
        raise HTTPException(503, 'Invalid follow-through source format')
    return rows


def _delivery(request, platform):
    from app.services import moses_resend_events as resend
    ledger = resend._ledger(request)
    events = _read_existing(ledger)
    # A missing signed-event ledger means delivery confirmation is unavailable.
    if events is None:
        return {'available': False, 'count': None, 'items': [],
                'note': 'No saved signed Resend events are available; delivery was not checked'}
    if any(not isinstance(e.get('provider_message_id'), str) or
           not isinstance(e.get('occurred_at'), str) or
           not isinstance(e.get('delivery_status'), str) for e in events):
        raise HTTPException(503, 'Malformed signed delivery history')
    latest = {}
    for event in events:
        ident = event['provider_message_id']
        key = (event['occurred_at'], str(event.get('event_id') or ''))
        if ident and (ident not in latest or key > latest[ident][0]):
            latest[ident] = (key, event['delivery_status'])
    problems = []
    sources = 0
    for kind in KINDS[platform]:
        actions = _read_existing(resend._action_file(request, platform, kind))
        if actions is None:
            continue
        sources += 1
        for action in actions:
            # Only joined provider observations for actual saved outgoing actions.
            ident = action.get('provider_message_id')
            if (action.get('state') != 'executed' or
                    not isinstance(ident, str) or ident not in latest):
                continue
            state = latest[ident][1]
            if state not in DELIVERY_PROBLEMS:
                continue
            record_id = str(action.get('record_id') or '')[:80]
            if not record_id:
                continue
            problems.append({
                'type': 'delivery', 'kind': kind, 'record_id': record_id,
                'title': DELIVERY_PROBLEMS[state], 'status': state,
                'when': latest[ident][0][0],
                'next_step': 'Review the saved delivery history and recipient before any resend',
            })
    # Keep only one most recent exception per kind/record; never show email addresses.
    dedup = {}
    for item in problems:
        key = (item['kind'], item['record_id'])
        if key not in dedup or item['when'] > dedup[key]['when']:
            dedup[key] = item
    items = sorted(dedup.values(), key=lambda r: r['when'], reverse=True)
    return {'available': bool(sources), 'count': len(items) if sources else None,
            'items': items[:20], 'limited_to': 20,
            'note': ('Only verified negative Resend events linked to saved sends are shown'
                     if sources else 'No supported saved send history is available')}


def _pds_work(request):
    store = getattr(request.app.state, 'calendar_store', None)
    if store is None or not hasattr(store, 'list_jobs'):
        return {'available': False, 'count': None, 'items': [],
                'note': 'PDS CalendarStore unavailable'}
    try:
        jobs = store.list_jobs()
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(503, 'PDS job list could not be verified') from exc
    if not isinstance(jobs, list) or any(not isinstance(j, dict) for j in jobs):
        raise HTTPException(503, 'PDS jobs returned an invalid record set')
    results = []
    for job in jobs:
        state = str(job.get('status') or '').strip().casefold()
        queue = next((kind for kind, states in PDS_WORK.items() if state in states), None)
        if not queue:
            continue
        exact_id = str(job.get('id') or '')
        if not exact_id or len(exact_id) > 80:
            continue
        results.append({'type': 'work', 'kind': queue, 'record_id': exact_id,
                        'job_number': str(job.get('job_number') or '')[:80],
                        'customer': str(job.get('customer') or '')[:100],
                        'status': str(job.get('status') or '')[:40],
                        'when': str(job.get('date') or '')[:40],
                        'title': {'needs_quote': 'Needs estimate review',
                                  'needs_invoice': 'Needs invoice review',
                                  'parts_on_order': 'Parts require follow-up'}[queue]})
    rank = {'needs_quote': 0, 'needs_invoice': 1, 'parts_on_order': 2}
    results.sort(key=lambda x: (rank[x['kind']], x['when'], x['job_number']))
    return {'available': True, 'count': len(results), 'items': results[:30],
            'limited_to': 30, 'note': 'Saved job statuses; not a claim that scope or pricing is complete'}


def _approvals(request):
    from app.services.moses_butler_flow import pending_actions
    try:
        pending = pending_actions(request)
    except HTTPException as exc:
        if exc.status_code in (503,):
            return {'available': False, 'count': None, 'items': [],
                    'note': 'Approval services are not enabled or unavailable'}
        raise
    rows = pending.get('proposals', [])
    return {'available': True, 'count': pending.get('count', len(rows)),
            'items': rows[:30], 'limited_to': 30,
            'note': 'Saved proposals, not executed actions'}



def _pds_drafts(request):
    """Read the real Moses PDS quote-review queue without mutating it.

    A missing queue is an empty *not-yet-prepared* queue. Existing malformed
    storage must not be presented as an empty or successfully checked queue.
    """
    path = Path(request.app.state.data_dir) / 'moses_pds' / 'quote_review_drafts.json'
    rows = _read_existing(path)
    if rows is None:
        return {'available': True, 'count': 0, 'items': [], 'limited_to': 30,
                'note': 'No saved Moses draft tickets yet; use Moses Drafts to prepare them'}
    allowed = {'pending_review': ('Review draft estimate', 0),
               'ready_for_estimator': ('Approved draft awaiting estimator', 1)}
    result = []
    for row in rows:
        state = row.get('state')
        if state not in allowed:
            continue
        draft_id = row.get('id')
        job_id = row.get('job_id')
        if (not isinstance(draft_id, str) or not isinstance(job_id, str)
                or not 1 <= len(draft_id) <= 80 or not 1 <= len(job_id) <= 80):
            raise HTTPException(503, 'Saved Moses draft identifiers are invalid')
        result.append({'type': 'draft', 'kind': state, 'record_id': job_id,
                       'draft_id': draft_id, 'title': allowed[state][0],
                       'customer': str(row.get('customer') or '')[:100],
                       'job_number': str(row.get('job_number') or '')[:80],
                       'status': state,
                       'when': str(row.get('updated_at') or row.get('created_at') or '')[:45]})
    result.sort(key=lambda item: (allowed[item['kind']][1], item['when'], item['job_number']))
    return {'available': True, 'count': len(result), 'items': result[:30],
            'limited_to': 30,
            'note': 'Saved Moses draft decisions; office review is not estimate issuance'}

def desk(request):
    workspace = _guard(request)
    return {'workspace': workspace, 'read_only': True, 'records_changed': False,
            'approvals': _approvals(request),
            'drafts': _pds_drafts(request) if workspace == 'pds' else
                {'available': False, 'count': None, 'items': [],
                 'note': 'PDS quote drafts are not used in this workspace'},
            'work': _pds_work(request) if workspace == 'pds' else
                {'available': False, 'count': None, 'items': [],
                 'note': 'PDS job queue is not used in this workspace'},
            'delivery': _delivery(request, workspace),
            'note': 'No emails resent, no estimates issued, and no jobs changed'}
