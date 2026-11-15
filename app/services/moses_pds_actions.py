"""Approval-only PDS status proposals using the existing CalendarStore API.

Independent PDS proposal storage. No direct JSON edits of PDS jobs.
Interrupted executions are quarantined rather than automatically replayed.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import RLock
from fastapi import HTTPException

_lock = RLock()


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != 'pds' or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'PDS office-admin access required')
    if os.getenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', '').lower().strip() != 'true':
        raise HTTPException(503, 'PDS Moses status actions disabled')


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else str(user)


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _store(request):
    store = getattr(request.app.state, 'calendar_store', None)
    if store is None or not all(hasattr(store, name) for name in ('get_job', 'update_job', '_lock')):
        raise HTTPException(503, 'PDS CalendarStore unavailable')
    return store


def _file(request):
    # Separate from SDC and Doorks workspace stores and CalendarStore records.
    path = Path(request.app.state.data_dir) / 'moses_pds' / 'status_proposals.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read(path):
    from app.routers.workspaces import load
    return load(path)


def _save(path, rows):
    from app.routers.workspaces import save
    save(path, rows)


def _hash(job):
    return sha256(json.dumps(job, sort_keys=True, default=str).encode()).hexdigest()


def _reconcile(rows, store):
    """Never replay an uncertain write; avoid duplicate side effects in CalendarStore."""
    changed = False
    for row in rows:
        if row.get('state') != 'executing':
            continue
        current = store.get_job(row['record_id'])
        if current is not None and _hash(current) == row['record_version']:
            # Original record unchanged: approval can be attempted again explicitly.
            row['state'] = 'pending'
        else:
            # CalendarStore itself may add status/approval/history fields. An
            # interrupted call cannot be conclusively classified from status alone.
            row['state'] = 'needs_review'
        row['recovered_at'] = _stamp()
        changed = True
    return changed


def propose(request, record_id, new_status):
    _guard(request)
    from app.services.calendar_store import STATUSES
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 80:
        raise HTTPException(422, 'Exact PDS job ID required')
    if new_status not in STATUSES or new_status in ('Additional Work', 'Complete/Additional Work'):
        raise HTTPException(422, 'Unsupported PDS status')
    store = _store(request)
    with _lock, store._lock:
        path = _file(request)
        rows = _read(path)
        if _reconcile(rows, store):
            _save(path, rows)
        job = store.get_job(record_id)
        if not job:
            raise HTTPException(404, 'PDS job not found')
        if job.get('status') == new_status:
            raise HTTPException(409, 'PDS job already has this status')
        proposal = {'id': uuid.uuid4().hex, 'kind': 'pds_job_status',
                    'record_id': record_id, 'job_number': str(job.get('job_number') or '')[:80],
                    'old_status': job.get('status'), 'new_status': new_status,
                    'record_version': _hash(job), 'state': 'pending',
                    'requested_by': _actor(request), 'requested_at': _stamp()}
        rows.append(proposal)
        _save(path, rows)
        return {'proposal': proposal, 'approval_required': True, 'executed': False}


def pending(request):
    _guard(request)
    store = _store(request)
    with _lock, store._lock:
        path = _file(request)
        rows = _read(path)
        if _reconcile(rows, store):
            _save(path, rows)
        waiting = [p for p in rows if p.get('state') in ('pending', 'needs_review')]
        return {'proposals': [{k: p.get(k) for k in ('id', 'kind', 'record_id', 'job_number',
                'old_status', 'new_status', 'state', 'requested_by', 'requested_at')}
                for p in waiting[-50:]], 'count': len(waiting), 'limited_to': 50}


def decide(request, proposal_id, approve):
    _guard(request)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Approval must be boolean')
    if not isinstance(proposal_id, str) or not re.fullmatch(r'[0-9a-f]{32}', proposal_id):
        raise HTTPException(422, 'Invalid proposal ID')
    store = _store(request)
    with _lock, store._lock:
        path = _file(request)
        rows = _read(path)
        if _reconcile(rows, store):
            _save(path, rows)
        proposal = next((p for p in rows if p.get('id') == proposal_id), None)
        if proposal is None:
            raise HTTPException(404, 'Proposal not found')
        if proposal['state'] != 'pending':
            raise HTTPException(409, 'Proposal decided or requires review')
        current = store.get_job(proposal['record_id'])
        if approve and (current is None or _hash(current) != proposal['record_version']):
            raise HTTPException(409, 'PDS job changed since proposal; create a new request')
        proposal['decided_by'] = _actor(request)
        proposal['decided_at'] = _stamp()
        if not approve:
            proposal['state'] = 'rejected'
            _save(path, rows)
            return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False,
                    'record_id': proposal['record_id']}
        # Write intent before calling CalendarStore. A crash cannot cause an
        # automatic repeat; ambiguous outcomes are held for manual review.
        proposal['state'] = 'executing'
        _save(path, rows)
        try:
            store.update_job(proposal['record_id'], {'status': proposal['new_status'],
                                                    'last_modified_by': _actor(request)})
            confirmed = store.get_job(proposal['record_id'])
            if confirmed is None or confirmed.get('status') != proposal['new_status']:
                raise RuntimeError('Saved PDS status could not be verified')
        except Exception as exc:
            proposal['state'] = 'needs_review'
            _save(path, rows)
            raise HTTPException(500, 'PDS execution requires review; do not retry blindly') from exc
        proposal['state'] = 'executed'
        proposal['confirmed_at'] = _stamp()
        _save(path, rows)
        return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                'record_id': proposal['record_id'], 'confirmed_status': confirmed['status']}
