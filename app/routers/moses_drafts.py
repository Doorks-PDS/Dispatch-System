"""PDS Moses quote-review tickets: durable, unpriced, never customer-facing documents.

Approval in this queue authorizes human preparation in the existing PDS estimator;
it does not approve, number, issue or email an estimate.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/moses-drafts', tags=['moses-drafts'])
QUOTE_STATUSES = frozenset(('quote', 'to be quoted', 'complete/quote'))
# A sent first estimate must not block reviewing *additional*, explicitly
# separated work. Legacy one-job reviews retain their stricter safeguards.
SEPARATE_SCOPE_STATUSES = QUOTE_STATUSES | frozenset(('quote sent',))
MAX_BATCH = 100


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != 'pds' or getattr(request.state, 'auth_role', None) not in ('office_admin','office','lead'):
        raise HTTPException(403, 'Active PDS office administrator required')
    return request.app.state.calendar_store


def _file(request):
    return Path(request.app.state.data_dir) / 'moses_pds' / 'quote_review_drafts.json'


@contextmanager
def _lock(path):
    # Shared across Render worker processes on an appropriately durable mounted data_dir.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a+b') as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)


def _read(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(503, 'Moses draft storage cannot be read; no changes made') from exc
    if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
        raise HTTPException(503, 'Moses draft storage invalid; no changes made')
    return data


def _write(path, rows):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp.unlink(missing_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _actor(request):
    user = request.state.auth_user
    if isinstance(user, dict):
        return str(user.get('id') or user.get('username') or 'office_admin')[:80]
    return 'office_admin'


def _usable_form(job):
    forms = job.get('completion_forms')
    if not isinstance(forms, list):
        return None
    for form in reversed(forms):
        if not isinstance(form, dict) or form.get('ready_to_quote') is not True:
            continue
        description = str(form.get('recommendations') or form.get('additional_recommendations') or '').strip()
        parts = str(form.get('parts_required') or '').strip()
        time_needed = str(form.get('time_required') or '').strip()
        if description or parts or time_needed:
            return form
    return None


def _form_digest(form):
    """Detect later edits to the recommendation the office actually reviewed."""
    fields = ('recommendations', 'additional_recommendations', 'parts_required', 'time_required', 'ready_to_quote')
    document = {key: form.get(key) for key in fields}
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _source_form(job, source_form_id):
    forms = job.get('completion_forms') if isinstance(job.get('completion_forms'), list) else []
    for form in forms:
        if isinstance(form, dict) and str(form.get('id') or form.get('created_at') or 'legacy') == source_form_id:
            return form
    return None


def _validate_source(store, item):
    try:
        job = store.get_job(item['job_id'])
    except (KeyError, AttributeError, OSError, TypeError, ValueError) as exc:
        raise HTTPException(409, 'PDS job cannot be verified; review the ticket') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != item['job_id']:
        raise HTTPException(409, 'Original PDS job could not be verified')
    status = str(job.get('status') or '').strip().casefold()
    separate_scope = bool(item.get('scope_key')) and isinstance(item.get('source_form_index'), int)
    allowed = SEPARATE_SCOPE_STATUSES if separate_scope else QUOTE_STATUSES
    if status not in allowed:
        raise HTTPException(409, 'Job is no longer in the quote queue')
    if str(job.get('sent_quote_number') or '').strip() and not separate_scope:
        raise HTTPException(409, 'An estimate has already been sent for this job')
    # Multi-scope reviews identify the exact source form by index as well as
    # digest. Legacy drafts continue to use their original form identifier.
    if 'source_form_index' in item:
        forms = job.get('completion_forms')
        index = item['source_form_index']
        if not isinstance(forms, list) or not isinstance(index, int) or index < 0 or index >= len(forms):
            raise HTTPException(409, 'Source completion form was removed or reordered')
        form = forms[index]
        if not isinstance(form, dict) or str(form.get('id') or form.get('created_at') or 'legacy') != item['source_form_id']:
            raise HTTPException(409, 'Original completion form identity changed')
    else:
        form = _source_form(job, item['source_form_id'])
    if not form or form.get('ready_to_quote') is not True:
        raise HTTPException(409, 'Recommendation form changed; review again')
    # Older ticket records predate form fingerprints. Do not accept an unverified
    # reference silently; refresh the ticket in office before issuing a document.
    if item.get('source_form_digest') != _form_digest(form):
        raise HTTPException(409, 'Recommendation scope changed; prepare a new review ticket')
    return job, form


def _verified_catalog_part(request, part_number):
    # Same source as GET /data/parts; no customer-facing prices inferred here.
    from app.routers.data import _parts_path
    path = _parts_path(request)
    if not path.is_file():
        raise HTTPException(409, 'PDS parts catalog unavailable; mark parts on hold')
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise HTTPException(503, 'Parts catalog could not be verified') from exc
    rows = document.get('items') if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise HTTPException(503, 'Parts catalog format invalid')
    found = [row for row in rows if isinstance(row, dict) and
             str(row.get('part_number') or '').strip().casefold() == part_number.casefold()]
    if len(found) != 1:
        raise HTTPException(409, 'Selected catalog part missing or ambiguous; review parts')
    return found[0]


def _checked_parts(request, selections):
    if not isinstance(selections, list) or len(selections) > 24:
        raise HTTPException(422, 'At most 24 selected catalog parts')
    checked = []
    seen = set()
    for line in selections:
        if not isinstance(line, dict) or set(line) != {'part_number', 'quantity'}:
            raise HTTPException(422, 'Each part requires an exact number and quantity')
        number = line['part_number']
        qty = line['quantity']
        if not isinstance(number, str) or not 1 <= len(number.strip()) <= 120 or number != number.strip():
            raise HTTPException(422, 'Invalid part number')
        if isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= 1000:
            raise HTTPException(422, 'Part quantity must be a whole number from 1 to 1000')
        if number.casefold() in seen:
            raise HTTPException(422, 'Duplicate catalog part selection')
        seen.add(number.casefold())
        catalog = _verified_catalog_part(request, number)
        checked.append({'part_number': number, 'quantity': qty,
                        'description': str(catalog.get('description') or '')[:220]})
    return checked


def _safe_ticket(row):
    # No internal notes, full forms, contact emails, or PDF attachment contents.
    allowed = ('id', 'job_id', 'job_number', 'customer', 'address', 'date', 'job_status',
               'state', 'scope', 'parts_required', 'parts_review', 'freight_review',
               'review_note', 'created_at', 'updated_at', 'version', 'source_form_id',
               'approved_at', 'approved_by', 'declined_at', 'declined_by', 'selected_parts', 'archived_at',
               'source_form_index', 'scope_title', 'scope_key', 'linked_estimate_number', 'linked_estimate_at', 'linked_estimate_by')
    return {k: row[k] for k in allowed if k in row}


@router.get('')
def list_drafts(request: Request):
    _guard(request)
    path = _file(request)
    # Listing must not create storage or silently erase existing records.
    if not path.exists():
        return {'items': [], 'count': 0, 'workspace': 'pds', 'storage': 'server_data_dir'}
    with _lock(path):
        items = _read(path)
    return {'items': [_safe_ticket(row) for row in items[-300:][::-1] if not row.get('archived_at')],
            'count': len(items), 'workspace': 'pds', 'storage': 'server_data_dir'}


@router.post('/prepare')
def prepare_batch(request: Request):
    store = _guard(request)
    try:
        jobs = store.list_jobs()
    except (AttributeError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'PDS jobs unavailable; no draft prepared') from exc
    if not isinstance(jobs, list):
        raise HTTPException(503, 'PDS jobs unavailable; no draft prepared')
    candidates = []
    for job in jobs:
        if not isinstance(job, dict) or str(job.get('status') or '').strip().casefold() not in QUOTE_STATUSES:
            continue
        if not str(job.get('id') or '').strip():
            continue
        if str(job.get('sent_quote_number') or '').strip():
            continue
        form = _usable_form(job)
        if form:
            candidates.append((job, form))
    path = _file(request)
    inserted = []
    with _lock(path):
        rows = _read(path)
        existing = {(str(x.get('job_id')), str(x.get('source_form_id'))) for x in rows}
        now = _now()
        for job, form in candidates:
            if len(inserted) >= MAX_BATCH:
                break
            identity = (str(job['id']), str(form.get('id') or form.get('created_at') or 'legacy'))
            # A job has one durable review ticket; old approved/declined decisions
            # are never overridden by a new scan.
            if any(str(x.get('job_id')) == identity[0] for x in rows):
                continue
            if identity in existing:
                continue
            scope = str(form.get('recommendations') or form.get('additional_recommendations') or '').strip()[:3000]
            item = {'id': uuid.uuid4().hex, 'job_id': identity[0],
                    'job_number': str(job.get('job_number') or '')[:80],
                    'customer': str(job.get('customer') or '')[:180],
                    'address': str(job.get('address') or '')[:220],
                    'date': str(job.get('date') or '')[:40],
                    'job_status': str(job.get('status') or '')[:60],
                    'source_form_id': identity[1], 'source_form_digest': _form_digest(form), 'scope': scope,
                    'parts_required': str(form.get('parts_required') or '').strip()[:2000],
                    'parts_review': 'needs_review' if str(form.get('parts_required') or '').strip() else 'none_specified',
                    'freight_review': 'not_assessed', 'review_note': '',
                    'state': 'pending_review', 'created_at': now,
                    'updated_at': now, 'version': 1}
            rows.append(item)
            inserted.append(_safe_ticket(item))
        if inserted:
            _write(path, rows)
    return {'created': len(inserted), 'eligible_jobs_checked': len(candidates),
            'items': inserted, 'batch_limited': len(candidates) > MAX_BATCH,
            'no_documents_issued': True}


class SpecificDraftRequest(BaseModel):
    record_id: str = Field(min_length=1, max_length=80)


@router.post('/prepare-job')
def prepare_specific_job(payload: SpecificDraftRequest, request: Request):
    """Create one unpriced PDS quote-review ticket for a verified exact job.

    No estimate, invoice, send or job update. Uses the exact same durable
    ledger, record fingerprint, authorizations and ticket schema as batch.
    """
    store = _guard(request)
    record_id = payload.record_id.strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', record_id):
        raise HTTPException(422, 'Use an exact internal PDS job ID')
    try:
        job = store.get_job(record_id)
    except (KeyError, AttributeError, OSError, TypeError, ValueError) as exc:
        raise HTTPException(404, 'PDS job not found') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != record_id:
        raise HTTPException(404, 'PDS job could not be verified')
    if str(job.get('status') or '').strip().casefold() not in QUOTE_STATUSES:
        raise HTTPException(409, 'This PDS job is not in the quote queue')
    if str(job.get('sent_quote_number') or '').strip():
        raise HTTPException(409, 'An estimate has already been sent for this job')
    form = _usable_form(job)
    if form is None:
        raise HTTPException(409, 'No ready-to-quote completion recommendation exists')
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        prior = next((item for item in rows if str(item.get('job_id')) == record_id), None)
        if prior is not None:
            # Never silently replace prior approval, decline or review decisions.
            return {'created': False, 'existing': True, 'item': _safe_ticket(prior),
                    'no_documents_issued': True, 'approval_required': True}
        now = _now()
        scope = str(form.get('recommendations') or form.get('additional_recommendations') or '').strip()[:3000]
        parts = str(form.get('parts_required') or '').strip()[:2000]
        item = {'id': uuid.uuid4().hex, 'job_id': record_id,
                'job_number': str(job.get('job_number') or '')[:80],
                'customer': str(job.get('customer') or '')[:180],
                'address': str(job.get('address') or '')[:220],
                'date': str(job.get('date') or '')[:40],
                'job_status': str(job.get('status') or '')[:60],
                'source_form_id': str(form.get('id') or form.get('created_at') or 'legacy'),
                'source_form_digest': _form_digest(form), 'scope': scope,
                'parts_required': parts,
                'parts_review': 'needs_review' if parts else 'none_specified',
                'freight_review': 'not_assessed', 'review_note': '',
                'state': 'pending_review', 'created_at': now,
                'updated_at': now, 'version': 1}
        rows.append(item)
        _write(path, rows)
    return {'created': True, 'existing': False, 'item': _safe_ticket(item),
            'no_documents_issued': True, 'approval_required': True}


class SeparateScope(BaseModel):
    source_form_index: int = Field(ge=0, le=100)
    title: str = Field(min_length=3, max_length=140)
    scope: str = Field(min_length=10, max_length=3000)


class SeparateScopesRequest(BaseModel):
    record_id: str = Field(min_length=1, max_length=80)
    scopes: list[SeparateScope] = Field(min_length=1, max_length=16)


@router.post('/prepare-job-scopes')
def prepare_job_scopes(payload: SeparateScopesRequest, request: Request):
    """Explicit human-separated, source-linked unpriced drafts in existing ledger.

    This does NOT split notes with AI, create estimates, modify jobs or issue
    documents. Duplicate requests reuse their original review tickets.
    """
    store = _guard(request)
    job_id = payload.record_id.strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
        raise HTTPException(422, 'Exact internal PDS job ID required')
    try:
        job = store.get_job(job_id)
    except (KeyError, AttributeError, OSError, TypeError, ValueError) as exc:
        raise HTTPException(503, 'PDS job unavailable') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != job_id:
        raise HTTPException(404, 'Verified PDS job not found')
    status = str(job.get('status') or '').strip().casefold()
    if status not in SEPARATE_SCOPE_STATUSES:
        raise HTTPException(409, 'Job is not in the quote queue')
    # Only the explicit per-form, per-scope preparation endpoint may proceed
    # after the first estimate is sent. Never clear the prior sent number or
    # change the job status; drafts still require independent office approval.
    forms = job.get('completion_forms')
    if not isinstance(forms, list):
        raise HTTPException(409, 'No saved completion forms')
    prepared = []
    for scope in payload.scopes:
        index = scope.source_form_index
        if index >= len(forms) or not isinstance(forms[index], dict):
            raise HTTPException(422, 'Source form index does not exist')
        form = forms[index]
        if form.get('ready_to_quote') is not True:
            raise HTTPException(409, 'Source completion form is not ready to quote')
        if not any(str(form.get(k) or '').strip() for k in ('recommendations', 'additional_recommendations', 'parts_required', 'time_required')):
            raise HTTPException(409, 'Source form contains no saved recommendation')
        title, description = scope.title.strip(), scope.scope.strip()
        if len(title) < 3 or len(description) < 10:
            raise HTTPException(422, 'Scope title and description required')
        source_id = str(form.get('id') or form.get('created_at') or 'legacy')
        digest = _form_digest(form)
        scope_key = hashlib.sha256(json.dumps([job_id,index,source_id,digest,title,description],ensure_ascii=False).encode()).hexdigest()
        prepared.append((index,source_id,digest,title,description,scope_key,form))
    if len({entry[5] for entry in prepared}) != len(prepared):
        raise HTTPException(422, 'Duplicate scopes in request')
    path = _file(request)
    result = []
    with _lock(path):
        rows = _read(path)
        existing = {str(r.get('scope_key')): r for r in rows if r.get('scope_key')}
        for index,source_id,digest,title,description,key,form in prepared:
            if key in existing:
                result.append({'created':False,'item':_safe_ticket(existing[key])})
                continue
            now = _now()
            parts = str(form.get('parts_required') or '').strip()[:2000]
            record = {'id':uuid.uuid4().hex,'job_id':job_id,
                'job_number':str(job.get('job_number') or '')[:80],
                'customer':str(job.get('customer') or '')[:180],
                'address':str(job.get('address') or '')[:220],
                'date':str(job.get('date') or '')[:40],
                'job_status':str(job.get('status') or '')[:60],
                'source_form_id':source_id,'source_form_index':index,
                'source_form_digest':digest,'scope_title':title,'scope_key':key,
                'scope':description,'parts_required':parts,
                'parts_review':'needs_review' if parts else 'none_specified',
                'freight_review':'not_assessed','review_note':'',
                'state':'pending_review','created_at':now,'updated_at':now,'version':1}
            rows.append(record)
            result.append({'created':True,'item':_safe_ticket(record)})
        if any(x['created'] for x in result):
            _write(path,rows)
    return {'workspace':'pds','job_id':job_id,'items':result,
            'created':sum(x['created'] for x in result),
            'no_documents_issued':True,'approval_required':True,
            'note':'Separate unpriced reviews; open each in Moses Drafts for parts, freight and estimator approval.'}


class DraftEdit(BaseModel):
    version: int = Field(ge=1)
    scope: str = Field(default='', max_length=3000)
    parts_review: str = Field(default='needs_review', max_length=30)
    freight_review: str = Field(default='not_assessed', max_length=30)
    review_note: str = Field(default='', max_length=1600)
    selected_parts: list[dict] = Field(default_factory=list, max_length=24)


class DraftDecision(BaseModel):
    version: int = Field(ge=1)
    approve: bool


def _find(rows, draft_id):
    if not re.fullmatch(r'[a-f0-9]{32}', draft_id):
        raise HTTPException(422, 'Invalid draft ID')
    item = next((x for x in rows if x.get('id') == draft_id), None)
    if item is None:
        raise HTTPException(404, 'Moses draft not found')
    return item


def _version(item, incoming):
    if item.get('version') != incoming:
        raise HTTPException(409, 'Draft changed since opening. Refresh before editing.')
    if item.get('state') != 'pending_review':
        raise HTTPException(409, 'This draft has already been decided')


@router.put('/{draft_id}')
def update_draft(draft_id: str, payload: DraftEdit, request: Request):
    _guard(request)
    if payload.parts_review not in ('needs_review', 'matched', 'new_part_needed', 'hold', 'none_specified'):
        raise HTTPException(422, 'Invalid parts review status')
    if payload.freight_review not in ('not_assessed', 'required', 'not_required', 'hold'):
        raise HTTPException(422, 'Invalid freight review status')
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        item = _find(rows, draft_id)
        _version(item, payload.version)
        checked_parts = _checked_parts(request, payload.selected_parts)
        if checked_parts and payload.parts_review != 'matched':
            raise HTTPException(409, 'Selected catalog parts must be marked matched')
        if payload.parts_review == 'matched' and not checked_parts:
            raise HTTPException(409, 'Select at least one verified catalog part before marking matched')
        item.update(scope=payload.scope.strip(), parts_review=payload.parts_review,
                    freight_review=payload.freight_review, review_note=payload.review_note.strip(),
                    selected_parts=checked_parts, updated_at=_now(), version=item['version'] + 1)
        _write(path, rows)
        return {'item': _safe_ticket(item), 'document_created': False}


@router.post('/{draft_id}/decide')
def decide_draft(draft_id: str, payload: DraftDecision, request: Request):
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office administrator approval required')
    store = _guard(request)
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        item = _find(rows, draft_id)
        _version(item, payload.version)
        if payload.approve:
            _validate_source(store, item)
            if item.get('parts_review') == 'matched':
                if not item.get('selected_parts'):
                    raise HTTPException(409, 'Saved parts selection is missing')
                _checked_parts(request, [{'part_number': p['part_number'], 'quantity': p['quantity']}
                                         for p in item['selected_parts']])
            if not item['scope'] and not item['parts_required']:
                raise HTTPException(409, 'Document scope or parts requirement is missing')
            if item['parts_review'] in ('needs_review', 'new_part_needed'):
                raise HTTPException(409, 'Review parts or mark them on hold before approval')
            if item['freight_review'] == 'not_assessed':
                raise HTTPException(409, 'Review freight before approving')
        stamp = _now()
        if payload.approve:
            item.update(state='ready_for_estimator', approved_by=_actor(request), approved_at=stamp)
        else:
            item.update(state='declined', declined_by=_actor(request), declined_at=stamp)
        item.update(updated_at=stamp, version=item['version'] + 1)
        _write(path, rows)
        return {'item': _safe_ticket(item), 'document_created': False,
                'email_sent': False, 'next_step': 'Open existing PDS estimator and review pricing before issuing' if payload.approve else 'No document created'}


@router.get('/{draft_id}/handoff')
def estimator_handoff(draft_id: str, request: Request):
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office administrator handoff required')
    """Revalidate reviewed ticket and return safe unsent estimator inputs.

    Never creates or prices a PDS estimate. Explicit freight review is passed as
    a label only; the estimator user must enter an actual freight amount.
    """
    store = _guard(request)
    path = _file(request)
    if not path.exists():
        raise HTTPException(404, 'No saved Moses review ticket')
    with _lock(path):
        item = dict(_find(_read(path), draft_id))
    if item.get('state') != 'ready_for_estimator':
        raise HTTPException(409, 'Approve the Moses draft review before opening the estimator')
    _validate_source(store, item)
    if not str(item.get('scope') or '').strip():
        raise HTTPException(409, 'Draft needs a documented work scope')
    if item.get('parts_review') in ('needs_review', 'new_part_needed') or item.get('freight_review') == 'not_assessed':
        raise HTTPException(409, 'Parts and freight decisions are incomplete')
    selected = item.get('selected_parts') or []
    # Re-read current catalog. Parts can be withdrawn after review.
    checked = _checked_parts(request, [{'part_number': p['part_number'], 'quantity': p['quantity']} for p in selected])
    if item.get('parts_review') == 'matched' and not checked:
        raise HTTPException(409, 'No verified parts selected')
    # Item descriptions and quantities only. No saved rate, cost, markup, or freight
    # amount can bypass the existing estimator's human review.
    return {'verified': True, 'workspace': 'pds', 'job_id': item['job_id'],
            'draft_id': item['id'], 'source_form_id': item['source_form_id'],
            'source_form_index': item.get('source_form_index'),
            'scope': item['scope'], 'selected_parts': checked,
            'parts_review': item['parts_review'], 'freight_review': item['freight_review'],
            'review_note': item.get('review_note') or '',
            'official_estimate_created': False, 'email_sent': False,
            'requires_pricing_review': True}


class DraftReopen(BaseModel):
    version: int = Field(ge=1)


@router.post('/{draft_id}/reopen')
def reopen_draft(draft_id: str, payload: DraftReopen, request: Request):
    """Explicitly return a reviewed ticket to office editing without issuing anything."""
    store = _guard(request)
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        item = _find(rows, draft_id)
        if item.get('version') != payload.version:
            raise HTTPException(409, 'Draft changed; refresh before reopening')
        if item.get('state') not in ('ready_for_estimator', 'declined'):
            raise HTTPException(409, 'Only decided tickets may return to review')
        _validate_source(store, item)
        stamp = _now()
        events = item.get('review_events') if isinstance(item.get('review_events'), list) else []
        events.append({'action': 'reopened', 'actor': _actor(request), 'at': stamp,
                       'previous_approval_at': item.get('approved_at', ''), 'previous_state': item.get('state')})
        item.update(state='pending_review', review_events=events[-30:],
                    updated_at=stamp, version=item['version'] + 1)
        _write(path, rows)
        return {'item': _safe_ticket(item), 'document_created': False,
                'note': 'Ticket returned to review; original approval preserved in history'}



@router.post('/{draft_id}/archive')
def archive_draft(draft_id: str, payload: DraftReopen, request: Request):
    """Hide an unwanted review while retaining decisions and audit history."""
    _guard(request)
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        item = _find(rows, draft_id)
        if item.get('version') != payload.version:
            raise HTTPException(409, 'Draft changed; refresh before archiving')
        if item.get('archived_at'):
            raise HTTPException(409, 'Draft is already archived')
        stamp = _now()
        events = item.get('review_events') if isinstance(item.get('review_events'), list) else []
        events.append({'action': 'archived', 'actor': _actor(request), 'at': stamp})
        item.update(archived_at=stamp, archived_by=_actor(request),
                    review_events=events[-30:], updated_at=stamp,
                    version=item['version'] + 1)
        _write(path, rows)
        return {'ok': True, 'archived': True, 'document_created': False,
                'email_sent': False}

def _linked_estimate_documents(request, draft_id):
    """Read-only linkage of approved Moses ticket to actual PDS estimate PDFs.

    Never guess from a customer name alone. The saved document must point to the
    exact job ID, or (for legacy documents) an exact, UNIQUE job number. The
    Resend service will independently validate PDF, recipient and contents.
    """
    store = _guard(request)
    path = _file(request)
    if not path.is_file():
        raise HTTPException(404, 'Moses draft not found')
    with _lock(path):
        item = dict(_find(_read(path), draft_id))
    if item.get('state') != 'ready_for_estimator':
        raise HTTPException(409, 'Approve the Moses review before preparing customer delivery')
    try:
        job = store.get_job(item['job_id'])
    except (AttributeError, KeyError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(409, 'Original PDS job cannot be verified') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != item['job_id']:
        raise HTTPException(409, 'Original PDS job no longer matches this draft')
    if str(job.get('job_number') or '') != str(item.get('job_number') or ''):
        raise HTTPException(409, 'Job number changed; verify document linkage')
    if str(job.get('customer') or '').strip().casefold() != str(item.get('customer') or '').strip().casefold():
        raise HTTPException(409, 'PDS customer changed; review before emailing')
    # A legacy number-only document is allowed ONLY if the job number resolves
    # uniquely in the current complete CalendarStore (never customer-name matching).
    jobs = store.list_jobs()
    if not isinstance(jobs, list):
        raise HTTPException(503, 'PDS jobs are unavailable')
    same_number = [j for j in jobs if isinstance(j, dict) and
                   str(j.get('job_number') or '').strip().casefold() ==
                   str(job.get('job_number') or '').strip().casefold()]
    unique_number = bool(job.get('job_number')) and len(same_number) == 1
    try:
        documents = request.app.state.documents_store.list_documents()
    except (AttributeError, OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'Saved PDS documents are unavailable') from exc
    if not isinstance(documents, list):
        raise HTTPException(503, 'Saved PDS documents are unavailable')
    matches = []
    for doc in documents:
        if not isinstance(doc, dict) or str(doc.get('type') or '').casefold() != 'estimate':
            continue
        number = str(doc.get('number') or '')
        if not re.fullmatch(r'RE[0-9]{5,}', number, re.I):
            continue
        doc_job_id = str(doc.get('job_id') or '').strip()
        doc_job_number = str(doc.get('job_number') or '').strip()
        if doc_job_id:
            if doc_job_id != item['job_id']:
                continue
        elif not (unique_number and doc_job_number and
                  doc_job_number.casefold() == str(job['job_number']).casefold()):
            continue
        if doc_job_number and doc_job_number.casefold() != str(job.get('job_number') or '').casefold():
            continue
        if str(doc.get('customer') or '').strip().casefold() != str(job.get('customer') or '').strip().casefold():
            continue
        matches.append({'kind': 'estimate', 'number': number,
                        'filename': str(doc.get('filename') or '')[:140],
                        'job_id': item['job_id'], 'customer': str(job['customer'])[:180]})
    # Multiple saved documents may exist for one job: NEVER select one implicitly.
    matches.sort(key=lambda r: r['number'], reverse=True)
    return matches[:30], len(matches)



class LinkSavedEstimate(BaseModel):
    version: int = Field(ge=1)
    estimate_number: str = Field(min_length=7, max_length=40)


@router.post('/{draft_id}/link-estimate')
def link_saved_estimate(draft_id: str, payload: LinkSavedEstimate, request: Request):
    """Explicitly associate one saved PDS estimate with ONE approved scope review.

    The estimator must have created the official document first. This action
    does not create, number, price, issue or send the document, and never writes
    to the CalendarStore or the official DocumentsStore.
    """
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office administrator approval required')
    _guard(request)
    number = payload.estimate_number.strip().upper()
    if not re.fullmatch(r'RE[0-9]{5,}', number):
        raise HTTPException(422, 'Select an existing PDS estimate number')
    # Read candidate documents BEFORE taking the draft-ledger lock; the
    # delivery helper takes its own ledger lock and must never be nested.
    candidates, _ = _linked_estimate_documents(request, draft_id)
    path = _file(request)
    with _lock(path):
        rows = _read(path)
        item = _find(rows, draft_id)
        if item.get('version') != payload.version:
            raise HTTPException(409, 'Draft changed; refresh before linking')
        if item.get('archived_at') or item.get('state') != 'ready_for_estimator':
            raise HTTPException(409, 'Only an active approved review can link an estimate')
        if not item.get('scope_key'):
            raise HTTPException(409, 'This is not a separately identified estimate scope')
        linked = str(item.get('linked_estimate_number') or '').upper()
        if linked and linked != number:
            raise HTTPException(409, 'Scope already linked to a different estimate; review the audit history')
        # Re-read the exact saved form without assuming the job still has Quote
        # status: sending the FIRST estimate may have moved it to Quote Sent.
        try:
            job = request.app.state.calendar_store.get_job(item['job_id'])
        except (AttributeError, OSError, ValueError, TypeError) as exc:
            raise HTTPException(503, 'PDS job unavailable') from exc
        if not isinstance(job, dict) or str(job.get('id') or '') != item['job_id']:
            raise HTTPException(409, 'Original job changed')
        if (str(job.get('job_number') or '') != str(item.get('job_number') or '') or
                str(job.get('customer') or '').strip().casefold() != str(item.get('customer') or '').strip().casefold()):
            raise HTTPException(409, 'Saved job identity changed')
        forms = job.get('completion_forms')
        index = item.get('source_form_index')
        if not isinstance(forms, list) or not isinstance(index, int) or not 0 <= index < len(forms):
            raise HTTPException(409, 'Original completion form no longer exists')
        form = forms[index]
        if (not isinstance(form, dict) or str(form.get('id') or form.get('created_at') or 'legacy') != item.get('source_form_id') or
                form.get('ready_to_quote') is not True or _form_digest(form) != item.get('source_form_digest')):
            raise HTTPException(409, 'Source recommendation changed; review before linking')
        for other in rows:
            if other.get('id') != draft_id and str(other.get('linked_estimate_number') or '').upper() == number:
                raise HTTPException(409, 'Estimate already linked to another Moses review scope')
        # _linked_estimate_documents checks verified job ID (or uniquely matched
        # legacy number), customer and document type. Never select by name alone.
        if number not in {str(doc.get('number') or '').upper() for doc in candidates}:
            raise HTTPException(409, 'Saved estimate does not match this exact PDS job')
        if linked == number:
            return {'ok': True, 'existing': True, 'item': _safe_ticket(item), 'document_created': False, 'sent': False}
        stamp = _now()
        events = item.get('review_events') if isinstance(item.get('review_events'), list) else []
        events.append({'action':'linked_saved_estimate', 'estimate_number':number, 'actor':_actor(request), 'at':stamp})
        item.update(linked_estimate_number=number, linked_estimate_at=stamp,
                    linked_estimate_by=_actor(request), review_events=events[-30:],
                    updated_at=stamp, version=item['version'] + 1)
        _write(path, rows)
        return {'ok':True, 'existing':False, 'item':_safe_ticket(item), 'document_created':False, 'sent':False}

@router.get('/{draft_id}/delivery')
def delivery_documents(draft_id: str, request: Request):
    """Offer exact saved estimate documents for this Moses review, without sending."""
    documents, total = _linked_estimate_documents(request, draft_id)
    path = _file(request)
    with _lock(path):
        item = dict(_find(_read(path), draft_id))
    is_separate = bool(item.get('scope_key'))
    number = str(item.get('linked_estimate_number') or '').upper()
    if is_separate and number:
        # Even after an estimate is linked, never offer delivery against a
        # recommendation that a technician subsequently edited or removed.
        try:
            source_job = request.app.state.calendar_store.get_job(item['job_id'])
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise HTTPException(503, 'PDS job unavailable') from exc
        forms = source_job.get('completion_forms') if isinstance(source_job, dict) else None
        index = item.get('source_form_index')
        if (not isinstance(forms, list) or not isinstance(index, int)
                or not 0 <= index < len(forms) or not isinstance(forms[index], dict)):
            raise HTTPException(409, 'Linked source form no longer exists; delivery blocked')
        form = forms[index]
        if (form.get('ready_to_quote') is not True or
                str(form.get('id') or form.get('created_at') or 'legacy') != item.get('source_form_id') or
                _form_digest(form) != item.get('source_form_digest')):
            raise HTTPException(409, 'Linked source recommendation changed; delivery blocked')
    if is_separate:
        for doc in documents:
            doc['linked_to_this_scope'] = doc['number'].upper() == number
        if number:
            # Once explicitly linked, never offer unrelated job estimates from
            # this draft-specific delivery endpoint.
            documents = [doc for doc in documents if doc['linked_to_this_scope']]
            total = len(documents)
        # Before linking, candidates are visible for office selection only;
        # the separate-scope UI must not offer their delivery actions.
    return {'workspace': 'pds', 'draft_id': draft_id, 'items': documents,
            'count': total, 'read_only': True, 'sent': False,
            'requires_scope_link': is_separate, 'linked_estimate_number': number or None,
            'note': ('Separate scope requires an explicit estimate link before offering delivery.'
                     if is_separate and not number else
                     'Select the explicitly linked estimate. Sending requires independent Resend approval.'
                     if is_separate else
                     'Select one official estimate PDF. Sending requires independent Resend approval.')}


# Moses part intake: explicit manual catalog creation; never infer catalog pricing from web results.
class MosesNewPart(BaseModel):
    part_number: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    manufacturer: str = Field(default='', max_length=160)
    supplier: str = Field(default='', max_length=160)
    price: str = Field(min_length=1, max_length=32)
    product_url: str = Field(default='', max_length=1500)
    confirm_create: bool = False


@router.post('/parts/intake/create')
def moses_create_catalog_part(payload: MosesNewPart, request: Request):
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office administrator catalog approval required')
    """PDS-admin, manual price, duplicate-safe one-click part intake.

    No purchase, automatic price lookup, or external action occurs.
    """
    _guard(request)
    if payload.confirm_create is not True:
        raise HTTPException(422, 'Explicit confirmation required before creating a catalog part')
    import decimal
    from app.routers.data import _parts_path, _part_https_url
    try:
        price = decimal.Decimal(payload.price.strip())
        if not price.is_finite() or price < 0 or price > decimal.Decimal('10000000') or price.as_tuple().exponent < -2:
            raise ValueError()
    except (ValueError, decimal.InvalidOperation):
        raise HTTPException(422, 'Enter a manually verified non-negative price with at most two decimal places')
    number = payload.part_number.strip()
    description = payload.description.strip()
    if not number or not description or any(c in number for c in '\r\n'):
        raise HTTPException(422, 'A valid part number and description are required')
    product_url = _part_https_url(payload.product_url) if payload.product_url.strip() else ''
    path = _parts_path(request)
    with _lock(path):
        try:
            catalog = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'items': []}
        except (OSError, UnicodeError, ValueError) as exc:
            raise HTTPException(503, 'PDS Parts List unavailable; no changes made') from exc
        if not isinstance(catalog, dict) or not isinstance(catalog.get('items'), list) or any(not isinstance(x, dict) for x in catalog['items']):
            raise HTTPException(503, 'PDS Parts List format invalid; no changes made')
        if any(str(x.get('part_number') or '').strip().casefold() == number.casefold() for x in catalog['items']):
            raise HTTPException(409, 'This part number is already in the catalog; use the existing part')
        row = {'id': uuid.uuid4().hex, 'manufacturer': payload.manufacturer.strip(),
               'part_number': number, 'description': description, 'supplier': payload.supplier.strip(),
               'price': str(price), 'image_url': '', 'product_url': product_url}
        catalog['items'].append(row)
        _write(path, catalog)
        return {'ok': True, 'item': row, 'created_by_moses_intake': True, 'estimate_created': False,
                'ordered': False, 'email_sent': False}
