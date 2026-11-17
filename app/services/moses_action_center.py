"""Conversation-facing read-only Moses action center.

Builds on the same saved PDS/Doorks/SDC records as the office Follow-Through
UI. It does not copy business state into conversation memory and never grants
write authority to the model. All permissions are enforced by existing code.
"""
from __future__ import annotations

from fastapi import HTTPException

_ALLOWED = ('pds', 'doorks', 'sdc')


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in to use Moses')
    platform = request.session.get('active_platform')
    if platform not in _ALLOWED or (getattr(request.state, 'auth_role', None) != 'office_admin' and not (platform == 'pds' and getattr(request.state, 'auth_role', None) in ('office','lead'))):
        raise HTTPException(403, 'Active workspace office administrator required')
    return platform


def _section(source, *, max_items=12):
    """Keep agent context bounded and distinguish unknown from empty."""
    if not isinstance(source, dict):
        raise HTTPException(503, 'A Moses work queue returned an invalid response')
    available = source.get('available') is True
    count = source.get('count') if available else None
    items = (source.get('items') or []) if available else []
    if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
        raise HTTPException(503, 'A Moses work queue contains invalid records')
    allowed = ('type', 'kind', 'record_id', 'draft_id', 'job_number', 'customer',
               'title', 'status', 'state', 'when', 'next_step', 'requested_at', 'id',
               'butler_action', 'workspace')
    safe = [{key: str(row[key])[:180] for key in allowed if key in row and row[key] is not None}
            for row in items[:max_items]]
    return {'available': available, 'count': count, 'shown': len(safe), 'items': safe,
            'note': str(source.get('note') or '')[:300]}


def overview(request):
    """Workspace-scoped, read-only, backed by saved ledgers and CalendarStore."""
    platform = _guard(request)
    from app.services.moses_followthrough import desk
    raw = desk(request)
    if not isinstance(raw, dict) or raw.get('workspace') != platform:
        raise HTTPException(503, 'Follow-Through returned the wrong workspace')
    payload = {
        'workspace': platform,
        'read_only': True,
        'approval_required_for_changes': True,
        'drafts': _section(raw.get('drafts', {'available': False,
                    'note': 'Draft queue not connected'})),
        'approvals': _section(raw.get('approvals', {})),
        'work': _section(raw.get('work', {})),
        'delivery': _section(raw.get('delivery', {})),
        'note': 'No job, document, email, part, payment, or customer record was changed.',
    }
    if platform != 'pds':
        payload['drafts'] = {'available': False, 'count': None, 'shown': 0,
                             'items': [], 'note': 'PDS quote drafts belong to PDS only'}
    return payload


def pds_draft_detail(request, draft_id: str):
    """A verified saved draft, never a fabricated estimate or priced document."""
    if _guard(request) != 'pds':
        raise HTTPException(403, 'PDS office workspace required')
    if not isinstance(draft_id, str) or not 1 <= len(draft_id) <= 80 or any(
            not (ch.isalnum() or ch in '_-') for ch in draft_id):
        raise HTTPException(422, 'Invalid saved draft identifier')
    from app.routers.moses_drafts import list_drafts
    saved = list_drafts(request)
    matches = [r for r in saved.get('items', []) if r.get('id') == draft_id]
    if len(matches) != 1:
        raise HTTPException(404, 'Draft not found in the saved PDS review list')
    row = matches[0]
    fields = ('id','job_id','job_number','customer','state','scope','parts_required',
              'parts_review','freight_review','review_note','version','updated_at')
    return {'workspace': 'pds', 'read_only': True,
            'draft': {k: row[k] for k in fields if k in row},
            'next_step': ('Open Moses Drafts to review. An office approval is required before estimator handoff.'
                          if row.get('state') == 'pending_review' else
                          'Open the existing PDS estimator using the verified saved handoff.'),
            'no_price_assumed': True, 'issued_estimate': False}
