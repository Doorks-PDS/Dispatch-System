"""Read-only PDS estimate readiness triage from the existing CalendarStore.

No independent queue, inferred pricing, automatic draft, or job mutation. The
source records must be re-read by the PDS editor when a user opens a job.
"""
from __future__ import annotations
from fastapi import HTTPException

QUOTE_STATUSES = frozenset({'to be quoted', 'quote', 'complete/quote'})
SCOPE_KEYS = ('recommendations', 'additional_recommendations', 'parts_required', 'time_required')


def _require_admin(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if (request.session.get('active_platform') != 'pds' or
            getattr(request.state, 'auth_role', None) not in ('office_admin','office','lead')):
        raise HTTPException(403, 'PDS office administrator access required')


def _clean(value, length=120):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return ''
    return ' '.join(str(value).split())[:length]


def _form_has_scope(form):
    return any(isinstance(form.get(key), str) and form[key].strip() for key in SCOPE_KEYS)


def _evaluate(job):
    forms = job.get('completion_forms')
    forms = [f for f in forms if isinstance(f, dict)] if isinstance(forms, list) else []
    marked = [f for f in forms if f.get('ready_to_quote') is True]
    documented = [f for f in forms if _form_has_scope(f)]
    ready_documented = [f for f in marked if _form_has_scope(f)]
    sent = _clean(job.get('sent_quote_number') or job.get('sent_estimate_number'))
    if sent:
        return 'review', 'A sent estimate is already linked; check it before preparing another', len(forms)
    if ready_documented:
        return 'ready', 'Quote-ready form has documented recommendations or required work; pricing needs office review', len(forms)
    if not forms:
        return 'missing', 'No saved completion or recommendation form', 0
    if marked:
        return 'review', 'Marked ready to quote, but the form has no documented recommendation scope', len(forms)
    if documented:
        return 'review', 'Recommendation details exist, but no form is marked ready to quote', len(forms)
    return 'missing', 'Saved form has no recommendation scope', len(forms)


def triage(request, *, limit=80):
    _require_admin(request)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise HTTPException(422, 'Limit must be between 1 and 100')
    store = getattr(request.app.state, 'calendar_store', None)
    if store is None or not hasattr(store, 'list_jobs'):
        raise HTTPException(503, 'PDS job records unavailable')
    try:
        rows = store.list_jobs()
    except (AttributeError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'PDS job records unavailable') from exc
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise HTTPException(503, 'PDS job record format invalid')
    buckets = {key: [] for key in ('ready', 'review', 'missing')}
    for job in rows:
        if str(job.get('status') or '').strip().casefold() not in QUOTE_STATUSES:
            continue
        classification, reason, forms = _evaluate(job)
        row = {key: _clean(job.get(key)) for key in ('id','job_number','customer','date','status','address')}
        if not row['id']:
            # An unidentifiable job must not be made clickable or mistaken for a valid draft source.
            classification = 'review' if classification == 'ready' else classification
            reason = 'Saved job has no verified ID; review it manually'
        row.update({'reason': reason, 'form_count': forms,
                    'can_prepare_estimate': classification == 'ready' and bool(row['id'])})
        buckets[classification].append(row)
    for group in buckets.values():
        group.sort(key=lambda r: (r.get('date') or '9999', r.get('job_number') or '', r.get('id') or ''))
    # Correct counts after any unidentifiable rows are quarantined.
    counts = {key: len(bucket) for key, bucket in buckets.items()}
    # Limit applies to displayed cards, not counts. Keep ready items ahead of review.
    remaining = limit
    output = []
    for key, label in [('ready','Ready for estimate review'),
                       ('review','Needs office review'),
                       ('missing','Missing recommendation details')]:
        shown = buckets[key][:remaining]
        remaining -= len(shown)
        output.append({'group':key,'label':label,'count':counts[key], 'jobs':shown})
    return {'workspace':'pds','read_only':True,'executed':False,'drafts_created':0,
            'records_changed':False,'total_needing_quote':sum(counts.values()),
            'counts':counts,'groups':output, 'display_limit':limit,
            'note':'Readiness is a form-content check, not approval or a completed estimate.'}


def summary(result):
    counts = result['counts']
    lines = [f"I reviewed {result['total_needing_quote']} saved PDS jobs needing quotes.",
             f"Ready for estimate review: {counts['ready']}.",
             f"Need office review: {counts['review']}.",
             f"Missing recommendation details: {counts['missing']}."]
    if counts['ready']:
        lines.append('Select Prepare Estimate on an eligible card to open the existing editable PDS estimator. Confirm scope, labor, parts, rates and tax before generating a document.')
    if counts['review'] or counts['missing']:
        lines.append('Other jobs need their saved forms checked or completed before Moses should suggest a quote.')
    lines.append('No estimate was created, priced, numbered, sent or approved; no jobs were changed.')
    return '\n'.join(lines)
