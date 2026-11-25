"""PDS-only saved document email via explicitly approved Resend actions.

Reads the existing DocumentsStore and CalendarStore. Does not create PDFs,
assign document numbers, change jobs, or use the local mail application.
Persist approvals on the configured business data directory; never silently
retry a potentially accepted provider request.
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
from fastapi import HTTPException

from app.services.moses_delivery import _email
from app.services.moses_mail_identity import identity

KINDS = {'estimate': 'RE', 'invoice': 'JS'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(request, kind=None):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in to use Moses')
    role = getattr(request.state, 'auth_role', None)
    if request.session.get('active_platform') != 'pds' or role not in ('office_admin', 'office', 'lead', 'tech'):
        raise HTTPException(403, 'PDS workspace document access required')
    if role == 'tech' and kind is not None and kind not in ('estimate', 'invoice'):
        raise HTTPException(403, 'Technicians may email estimates and invoices only')


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else 'office_admin'


def _file(request):
    return Path(request.app.state.data_dir) / 'moses_pds_document_delivery_actions.json'


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _load(path):
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Document email approval ledger cannot be read') from exc
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise HTTPException(503, 'Document email approval ledger is invalid')
    return rows


def _save(path, rows):
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _snapshot(request, kind, number):
    _guard(request, kind)
    prefix = KINDS.get(kind)
    if not prefix or not re.fullmatch(prefix + r'[0-9]{5,}', number or '', re.I):
        raise HTTPException(422, 'Use an exact saved estimate or invoice number')
    store = request.app.state.documents_store
    rows = [r for r in store.list_documents() if isinstance(r, dict)
            and str(r.get('type') or '').lower() == kind
            and str(r.get('number') or '').upper() == number.upper()]
    if len(rows) != 1:
        raise HTTPException(404, 'Saved PDS document was not uniquely found')
    doc = rows[0]
    if doc.get('_read_only_pdf_fallback'):
        raise HTTPException(409, 'Document metadata must be reconciled before sending')
    filename = str(doc.get('filename') or '')
    if filename != str(doc.get('number')) + '.pdf' or filename != Path(filename).name:
        raise HTTPException(409, 'Saved document filename does not match the number')
    # Files must be inside the configured document directory, never a path from
    # user-controlled metadata. Require the actual saved PDF (not a new render).
    pdf_path = (store.dir / filename).resolve()
    if pdf_path.parent != store.dir.resolve() or not pdf_path.is_file():
        raise HTTPException(409, 'Saved PDS PDF is missing')
    if pdf_path.stat().st_size > 10 * 1024 * 1024:
        raise HTTPException(409, 'PDF exceeds permitted email attachment size')
    raw = pdf_path.read_bytes()
    if not raw.startswith(b'%PDF') or not raw:
        raise HTTPException(409, 'Saved PDF is invalid')
    jobs = request.app.state.calendar_store.list_jobs()
    if not isinstance(jobs, list):
        raise HTTPException(503, 'PDS jobs cannot be verified')
    doc_job_id = str(doc.get('job_id') or '').strip()
    doc_job_num = str(doc.get('job_number') or '').strip()
    if not doc_job_id and not doc_job_num:
        raise HTTPException(409, 'Document has no verified job linkage')
    matched = [j for j in jobs if isinstance(j, dict) and (
        (doc_job_id and str(j.get('id') or '') == doc_job_id) or
        (not doc_job_id and doc_job_num and str(j.get('job_number') or '').casefold() == doc_job_num.casefold()))]
    if len(matched) != 1:
        raise HTTPException(409, 'Document must link to one unique PDS job')
    job = matched[0]
    # Reject stale job links and mismatched customer names; do not send a PDF
    # about one account to a contact selected from another account.
    if doc_job_num and str(job.get('job_number') or '').casefold() != doc_job_num.casefold():
        raise HTTPException(409, 'Linked job number mismatch')
    doc_customer = str(doc.get('customer') or '').strip().casefold()
    job_customer = str(job.get('customer') or job.get('customer_name') or '').strip().casefold()
    if not doc_customer or not job_customer or ' '.join(doc_customer.split()) != ' '.join(job_customer.split()):
        raise HTTPException(409, 'Document customer and job customer require review')
    recipient = _email(job.get('contact_email') or job.get('email') or job.get('customer_email'))
    if not recipient:
        raise HTTPException(409, 'Linked job has no verified contact email')
    mail = identity('pds', kind)
    if mail['issues']:
        raise HTTPException(503, '; '.join(mail['issues']))
    return {'workspace': 'pds', 'kind': kind, 'number': str(doc['number']),
            'filename': filename, 'job_id': str(job.get('id') or ''),
            'job_number': str(job.get('job_number') or ''), 'customer': str(doc['customer']),
            'to': recipient, 'from': mail['from'], 'reply_to': mail['reply_to'],
            'cc': mail['cc'], 'subject': kind.title() + ' ' + str(doc['number']),
            'pdf_sha256': hashlib.sha256(raw).hexdigest(), 'pdf_size': len(raw)}


def preview(request, kind, number):
    snap = _snapshot(request, kind, number)
    return {k: v for k, v in snap.items() if k != 'pdf_sha256'} | {
        'attachment_verified': True, 'ready_for_approval': True,
        'sent': False, 'approval_required': True,
        'send_enabled': os.getenv('MOSES_PDS_DOCUMENT_SEND_ENABLED', '').strip().lower() == 'true',
        'requires_office_review': getattr(getattr(request, 'state', None), 'auth_role', None) == 'tech'}


def _fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode('utf-8')).hexdigest()


def _public(row):
    snap = row['snapshot']
    return {'id': row['id'], 'state': row['state'], 'kind': snap['kind'],
            'number': snap['number'], 'job_number': snap['job_number'],
            'to': snap['to'], 'from': snap['from'], 'reply_to': snap['reply_to'],
            'subject': snap['subject'], 'filename': snap['filename'],
            'approved': row['state'] in ('sending', 'sent', 'uncertain'),
            'requested_by': row.get('requested_by'),
            'requested_role': row.get('requested_role'),
            'job_id': snap.get('job_id'),
            'ready_label': 'Quote Ready' if snap['kind'] == 'estimate' else 'Invoice Ready',
            'requires_office_review': row.get('requested_role') == 'tech',
            'sent': row['state'] == 'sent', 'delivery_status': row.get('delivery_status'),
            'provider_message_id': row.get('provider_message_id'),
            'requested_at': row.get('requested_at'), 'completed_at': row.get('completed_at'),
            'cc': snap.get('cc'), 'attachment_filename': snap.get('filename')}


def review_queue(request):
    """Office-only inbox for technician estimate/invoice reviews.

    Quote Ready and Invoice Ready are document-review states, not job statuses.
    """
    _guard(request)
    if getattr(request.state, 'auth_role', None) not in ('office', 'office_admin'):
        raise HTTPException(403, 'Office access required to review technician documents')
    path = _file(request)
    with _locked(path):
        rows = [r for r in _load(path) if r.get('state') == 'pending'
                and r.get('requested_role') == 'tech'
                and r.get('snapshot', {}).get('kind') in ('estimate', 'invoice')]
        items = [_public(r) for r in rows]
    items.sort(key=lambda r: str(r.get('requested_at') or ''))
    return {'count': len(items), 'items': items, 'workspace': 'pds',
            'approval_required': True}


def propose(request, kind, number):
    snap = _snapshot(request, kind, number)
    path = _file(request)
    with _locked(path):
        rows = _load(path)
        if any(r.get('snapshot', {}).get('kind') == kind and r.get('snapshot', {}).get('number') == number
               and r.get('state') in ('sending', 'uncertain') for r in rows):
            raise HTTPException(409, 'Prior send outcome requires manual provider review')
        fp = _fingerprint(snap)
        prior = next((r for r in rows if r.get('fingerprint') == fp and r.get('state') in ('pending', 'sent')), None)
        if prior:
            if prior.get('state') == 'pending' and getattr(request.state, 'auth_role', None) in ('tech', 'lead') and prior.get('requested_by') != _actor(request):
                raise HTTPException(409, 'Another employee has an active approval for this document')
            if prior['state'] == 'sent':
                raise HTTPException(409, 'Already sent; review delivery history before resending')
            return {'proposal': _public(prior), 'approval_required': True, 'sent': False}
        row = {'id': uuid.uuid4().hex, 'state': 'pending', 'snapshot': snap,
               'fingerprint': fp, 'requested_at': _now(), 'requested_by': _actor(request),
               'requested_role': str(getattr(request.state, 'auth_role', '') or '')}
        rows.append(row)
        _save(path, rows)
        return {'proposal': _public(row), 'approval_required': True, 'sent': False}


def _sync_sent_document_status(request, snapshot):
    """Move one verified PDS job only after Resend accepts its document.

    Never mutate status on preview, draft, approval proposal or uncertain send.
    This is best-effort: a successful external send is never retried just because
    the internal status write failed. An error is returned for office follow-up.
    """
    store = request.app.state.calendar_store
    job_id = str(snapshot.get('job_id') or '').strip()
    job = store.get_job(job_id)
    if not job or str(job.get('job_number') or '') != str(snapshot.get('job_number') or ''):
        raise RuntimeError('Linked PDS job changed after document send')
    kind = snapshot['kind']
    current = str(job.get('status') or '')
    updates = {}
    if kind == 'estimate':
        # Never overwrite the original Estimate # or an earlier sent estimate.
        if current not in {'Quote', 'Complete/Quote', 'To Be Quoted'}:
            return current
        target = 'Quote Sent'
        if not str(job.get('sent_quote_number') or '').strip():
            updates['sent_quote_number'] = snapshot['number']
    elif kind == 'invoice':
        # A draft invoice is not proof of completion. Only completed work can
        # move to Done after the document is accepted by Resend.
        if current == 'Done':
            return current
        if current not in {'Complete', 'Complete/Quote', 'To Be Invoiced'}:
            return current
        target = 'Done'
    else:
        return current
    updates['status'] = target
    updated = store.update_job(job_id, updates)
    if str(updated.get('status') or '') != target:
        raise RuntimeError('PDS job status update not verified')
    return target


def decide(request, proposal_id, approve):
    _guard(request)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Explicit approval decision required')
    if not re.fullmatch(r'[a-f0-9]{32}', proposal_id or ''):
        raise HTTPException(422, 'Invalid proposal ID')
    path = _file(request)
    with _locked(path):
        rows = _load(path)
        row = next((r for r in rows if r.get('id') == proposal_id), None)
        if not row:
            raise HTTPException(404, 'Email proposal not found')
        _guard(request, row.get('snapshot', {}).get('kind'))
        if getattr(request.state, 'auth_role', None) in ('tech', 'lead') and row.get('requested_by') != _actor(request):
            raise HTTPException(403, 'You may decide only an email you prepared')
        if row['state'] != 'pending':
            raise HTTPException(409, 'Proposal already processed')
        role = str(getattr(request.state, 'auth_role', '') or '')
        # Enforce in the backend: technician approval may never contact Resend.
        if approve and role == 'tech':
            raise HTTPException(403, 'Technician documents must be reviewed and sent by Office')
        if approve and row.get('requested_role') == 'tech' and role not in ('office', 'office_admin'):
            raise HTTPException(403, 'Office review is required for technician documents')
        if not approve:
            row.update(state='rejected', decided_by=_actor(request), decided_at=_now())
            _save(path, rows)
            return {'state': 'rejected', 'sent': False}
        snap = row['snapshot']
        fresh = _snapshot(request, snap['kind'], snap['number'])
        if _fingerprint(fresh) != row['fingerprint']:
            row.update(state='stale', decided_at=_now())
            _save(path, rows)
            raise HTTPException(409, 'PDF, recipient, or job changed; create a new proposal')
        if os.getenv('MOSES_PDS_DOCUMENT_SEND_ENABLED', '').strip().lower() != 'true':
            raise HTTPException(503, 'PDS Resend document emailing is not enabled')
        from app.services.moses_email_transport import ready, send_resend_attachment
        ready(snap['from'])
        # Persist the send intent BEFORE contacting Resend. Unknown response
        # always remains an uncertain hold instead of an automatic retry.
        row.update(state='sending', decided_by=_actor(request), decided_at=_now())
        _save(path, rows)
        message = {'from': snap['from'], 'to': snap['to'], 'reply_to': snap['reply_to'],
                   'subject': snap['subject'],
                   'text': ('Please review the attached ' + snap['kind'] + ' ' + snap['number'] +
                            ' for ' + snap['customer'] + '.\n\nReply to this message with questions.')}
        key = hashlib.sha256((row['id'] + row['fingerprint']).encode()).hexdigest()
        try:
            content = (request.app.state.documents_store.dir / snap['filename']).read_bytes()
            if hashlib.sha256(content).hexdigest() != snap['pdf_sha256']:
                raise RuntimeError('Document changed during send preparation')
            provider_id = send_resend_attachment(message, content, snap['filename'],
                                                  'application/pdf', idempotency_key=key)
        except Exception:
            row.update(state='uncertain', completed_at=_now())
            _save(path, rows)
            return {'state': 'uncertain', 'sent': False, 'message': 'Resend outcome unconfirmed; inspect provider delivery history before retrying'}
        row.update(state='sent', completed_at=_now(), provider_message_id=provider_id,
                   delivery_status='accepted_by_provider')
        _save(path, rows)
        # The email was already accepted. Never attempt another send if status
        # synchronization fails; show the follow-up rather than claiming success.
        try:
            job_status = _sync_sent_document_status(request, snap)
            row['job_status'] = job_status
            row['status_sync'] = 'verified'
        except Exception:
            import logging
            logging.getLogger(__name__).exception('PDS document sent but job status sync failed')
            row['status_sync'] = 'needs_review'
        _save(path, rows)
        return {'state': 'sent', 'sent': True, 'provider_message_id': provider_id,
                'delivery_status': 'accepted_by_provider',
                'status_sync': row['status_sync'], 'job_status': row.get('job_status')}


def _delivery_events(request, provider_ids):
    """Read only the existing, signature-verified Resend event ledger.

    This does NOT fetch customer data or send mail. Events are written by the
    existing signed webhook. Absent events must never be called delivered.
    """
    if not provider_ids:
        return {}
    path = Path(request.app.state.data_dir) / 'moses_resend_delivery_events.json'
    if not path.exists():
        return {}
    # The webhook uses this exact flock path while updating its ledger. A
    # corrupt ledger fails closed instead of silently showing a false status.
    from app.services.moses_resend_events import _locked as events_locked
    with events_locked(path):
        try:
            rows = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise HTTPException(503, 'Resend delivery event history cannot be read') from exc
    if not isinstance(rows, list):
        raise HTTPException(503, 'Resend delivery event history is invalid')
    # Do not apply an event to any document other than the one whose Resend
    # provider message ID matches. If multiple events exist, use event time,
    # not arrival order, with event ID as a deterministic tie-breaker.
    latest = {}
    for event in rows:
        if not isinstance(event, dict):
            raise HTTPException(503, 'Resend delivery event history is invalid')
        provider_id = event.get('provider_message_id')
        if provider_id not in provider_ids:
            continue
        occurred = event.get('occurred_at')
        event_id = event.get('event_id')
        state = event.get('delivery_status')
        from app.services.moses_resend_events import EVENT_STATES
        if (not isinstance(occurred, str) or not isinstance(event_id, str)
                or state not in EVENT_STATES.values()):
            raise HTTPException(503, 'Resend delivery event history is invalid')
        key = (occurred, event_id)
        if provider_id not in latest or key > latest[provider_id][0]:
            latest[provider_id] = (key, state)
    return {provider_id: {'delivery_status': item[1],
                          'delivery_event_at': item[0][0]}
            for provider_id, item in latest.items()}


def history(request, kind, number):
    _guard(request, kind)
    prefix = KINDS.get(kind)
    if not prefix or not re.fullmatch(prefix + r'[0-9]{5,}', number or '', re.I):
        raise HTTPException(422, 'Use an exact saved estimate or invoice number')
    path = _file(request)
    with _locked(path):
        rows = [r for r in _load(path)
                if r.get('snapshot', {}).get('kind') == kind
                and str(r.get('snapshot', {}).get('number') or '').upper() == number.upper()][-50:]
    provider_ids = {r.get('provider_message_id') for r in rows
                    if isinstance(r.get('provider_message_id'), str) and r['provider_message_id']}
    events = _delivery_events(request, provider_ids)
    output = []
    for row in rows:
        item = _public(row)
        # 'sent' means Resend accepted the request, not recipient delivery.
        observed = events.get(row.get('provider_message_id'))
        if observed:
            item.update(observed)
        else:
            item['delivery_status'] = ('not_confirmed' if row.get('state') in ('sending', 'uncertain')
                                       else (row.get('delivery_status') or 'not_sent'))
            item['delivery_event_at'] = None
        output.append(item)
    return output
