"""Read-only compare and explicitly authorized changes from PDS document intake.

No AI decisions are trusted as authority; a saved exact job number determines target.
This adapter only handles document reference fields and notes, not identity or status.
"""
import hashlib
import json
from fastapi import HTTPException

FIELDS = ('estimate_number', 'po_number', 'invoice_number', 'job_notes', 'office_notes')
SNAPSHOT_FIELDS = ('id','job_number','customer','address','updated_at', *FIELDS)


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != 'pds' or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'PDS office administrator required')


def _fingerprint(job):
    return hashlib.sha256(json.dumps({k: job.get(k) for k in SNAPSHOT_FIELDS}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _safe(v, maximum=4000):
    if not isinstance(v, str) or len(v) > maximum or '\x00' in v:
        raise HTTPException(422, 'Invalid document field')
    return v.strip()


def _target(request, job_number):
    number = _safe(job_number, 90)
    if not number:
        raise HTTPException(422, 'An exact saved job number is required')
    try:
        rows = request.app.state.calendar_store.list_jobs()
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise HTTPException(503, 'PDS saved job records unavailable') from exc
    if not isinstance(rows, list):
        raise HTTPException(503, 'PDS saved job records unavailable')
    matches = [j for j in rows if isinstance(j, dict) and str(j.get('job_number') or '').strip().casefold() == number.casefold()]
    if len(matches) != 1 or not matches[0].get('id'):
        raise HTTPException(409, 'Job reference is missing or ambiguous; open the saved ticket manually')
    job = request.app.state.calendar_store.get_job(str(matches[0]['id']))
    if not isinstance(job, dict) or str(job.get('id')) != str(matches[0]['id']):
        raise HTTPException(409, 'Saved job could not be verified')
    return job


def _validate_reference(request, job, estimate_number):
    number = _safe(estimate_number, 90)
    if not number:
        return
    current = {str(job.get(k) or '').strip().casefold() for k in ('estimate_number','sent_quote_number')}
    if number.casefold() in current:
        return
    try:
        rows = request.app.state.calendar_store.list_jobs()
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise HTTPException(503, 'PDS job records unavailable') from exc
    for row in rows:
        if not isinstance(row, dict) or str(row.get('id') or '') == str(job['id']):
            continue
        if number.casefold() in (str(row.get('estimate_number') or '').strip().casefold(),
                                 str(row.get('sent_quote_number') or '').strip().casefold()):
            raise HTTPException(409, 'Estimate number belongs to a different saved job; review manually')


def compare(request, job_number, fields):
    _guard(request)
    if not isinstance(fields, dict):
        raise HTTPException(422, 'Invalid extracted document')
    job = _target(request, job_number)
    _validate_reference(request, job, str(fields.get('estimate_number') or ''))
    changes = []
    for key in FIELDS:
        suggested = fields.get(key)
        if suggested is None or suggested == '':
            continue
        proposed = _safe(suggested, 4000 if key.endswith('notes') else 90)
        old = str(job.get(key) or '').strip()
        if proposed and proposed != old:
            changes.append({'field': key, 'saved_value': old[:4000], 'suggested_value': proposed,
                            'would_replace_existing': bool(old), 'selected': False})
    return {'job_id': str(job['id']), 'job_number': str(job['job_number']),
            'customer': str(job.get('customer') or '')[:150], 'address': str(job.get('address') or '')[:250],
            'version': _fingerprint(job), 'changes': changes,
            'read_only': True, 'records_changed': False,
            'identity_locked': True,
            'message': 'Select each change to apply. Customer, service address, and job status are never changed here.'}


def apply(request, job_number, expected_version, changes, confirmed):
    _guard(request)
    if confirmed is not True:
        raise HTTPException(422, 'Explicit review confirmation required')
    if not isinstance(changes, dict) or not changes or len(changes) > len(FIELDS) or not set(changes).issubset(FIELDS):
        raise HTTPException(422, 'Choose one or more allowed fields')
    if not isinstance(expected_version, str) or len(expected_version) != 64:
        raise HTTPException(422, 'Valid saved-record version required')
    updates = {k: _safe(v, 4000 if k.endswith('notes') else 90) for k, v in changes.items()}
    if any(not v for v in updates.values()):
        raise HTTPException(422, 'Empty values cannot replace saved fields')
    store = request.app.state.calendar_store
    # The lock is shared with the existing CalendarStore writer (RLock).
    with store._lock:
        job = _target(request, job_number)
        if _fingerprint(job) != expected_version:
            raise HTTPException(409, 'Job changed since review; refresh differences before applying')
        if 'estimate_number' in updates:
            _validate_reference(request, job, updates['estimate_number'])
        if all(str(job.get(k) or '').strip() == v for k, v in updates.items()):
            return {'updated': False, 'job_id': str(job['id']), 'fields_changed': [], 'already_applied': True}
        user = request.state.auth_user
        updates['last_modified_by'] = str(user.get('name') or user.get('username') or user.get('id') or 'office_admin') if isinstance(user, dict) else 'office_admin'
        updated = store.update_job(str(job['id']), updates)
        if any(str(updated.get(k) or '').strip() != v for k,v in updates.items() if k in FIELDS):
            raise HTTPException(500, 'Saved changes could not be confirmed')
        return {'updated': True, 'job_id': str(job['id']), 'fields_changed': list(changes),
                'saved_version': _fingerprint(updated), 'records_changed': True}
