"""Read-only grouping of saved PDS recommendation/completion forms for estimator review.

One form is a proposed scope, never an automatically issued estimate. A form
that calls for multiple quotes stays intact and is flagged for manual splitting.
No customer messages, estimate numbers, prices, or job data are changed here.
"""
from __future__ import annotations
import re
from fastapi import HTTPException

_SEPARATE = re.compile(r'\b(?:separate|multiple|individual|different)\s+(?:quotes?|estimates?)\b|\b(?:quotes?|estimates?)\s+(?:separately|for each|per opening|per location)\b|\b(?:two|three|four|2|3|4)\s+(?:quotes?|estimates?)\b', re.I)
_SCOPE_FIELDS = ('recommendations', 'additional_recommendations', 'parts_required', 'time_required')


def inspect(request, job_id: str):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if (request.session.get('active_platform') != 'pds' or
            getattr(request.state, 'auth_role', None) not in ('office_admin', 'office', 'lead')):
        raise HTTPException(403, 'PDS office access required')
    if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
        raise HTTPException(422, 'Exact PDS job ID required')
    store = getattr(request.app.state, 'calendar_store', None)
    if store is None:
        raise HTTPException(503, 'PDS jobs unavailable')
    try:
        job = store.get_job(job_id)
    except (OSError, TypeError, ValueError) as exc:
        raise HTTPException(503, 'Unable to read saved job') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != job_id:
        raise HTTPException(404, 'Verified PDS job not found')
    forms = job.get('completion_forms')
    if not isinstance(forms, list):
        forms = []
    output = []
    for index, form in enumerate(forms):
        if not isinstance(form, dict):
            continue
        details = {key: str(form.get(key) or '').strip()[:1200] for key in _SCOPE_FIELDS}
        technician_notes = str(form.get('tech_notes') or form.get('technician_notes') or '').strip()[:1200]
        # A technician may record separate-quote instructions only in Tech Notes.
        # Keep those source words for office review, but don't promote every
        # routine PM completion into an estimate scope.
        if technician_notes and (_SEPARATE.search(technician_notes) or re.search(
                r'\b(?:recommend(?:ed)?|leaking|worn|replace|corrective repair)\b', technician_notes, re.I)):
            details['technician_observations'] = technician_notes
        if not any(details.values()):
            continue
        notes = ' '.join(details.values())
        # Use source form IDs only; do not fabricate new form identifiers.
        source_id = str(form.get('id') or '').strip()[:80]
        output.append({
            'source_form_id': source_id or None,
            'source_form_index': index,
            'source_form_number': index + 1,
            'door_location': str(form.get('door_location') or '').strip()[:180],
            'door_type': str(form.get('door_type') or '').strip()[:100],
            'ready_to_quote': form.get('ready_to_quote') is True,
            'scope': details,
            'split_review_required': bool(_SEPARATE.search(notes)),
            'status': 'needs_manual_split' if _SEPARATE.search(notes) else
                      'ready_for_office_review' if form.get('ready_to_quote') is True else
                      'needs_quote_readiness_review',
        })
    split = any(item['split_review_required'] for item in output)
    return {
        'workspace': 'pds', 'read_only': True, 'job_id': job_id,
        'job_number': str(job.get('job_number') or '')[:80],
        'form_count': sum(isinstance(f, dict) for f in forms),
        'proposed_scope_count': len(output), 'manual_split_required': split,
        'proposed_scopes': output,
        'note': ('One proposed scope per source form; scope grouping requires office confirmation. '
                 'If one form references separate estimates, review and split it manually. '
                 'No estimate, document, price, approval, or job was created or changed.'),
    }
