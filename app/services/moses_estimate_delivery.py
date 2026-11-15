"""Explicitly approved estimate PDF + customer acceptance email (Doorks/SDC).

Fails closed until configured. Uses the existing SMTP sender and acceptance service.
Unknown SMTP outcomes are NEVER retried automatically. No raw portal tokens in logs.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import fcntl
import hashlib
import json
import os
import uuid

from fastapi import HTTPException

from app.routers.workspaces import guard, location, load, save
from app.services import moses_estimate_acceptance as acceptance
from app.services.moses_delivery import _email, _find_record
from app.services.moses_po_delivery import _transmit


def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(request, platform):
    if platform not in ('doorks', 'sdc'):
        raise HTTPException(404, 'Unsupported workspace')
    guard(request, platform, 'estimates_invoices')
    if os.getenv('MOSES_ESTIMATE_SEND_ENABLED', '').strip().lower() != 'true':
        raise HTTPException(503, 'Estimate emailing is disabled')


def _origin():
    raw = os.getenv('MOSES_PUBLIC_BASE_URL', '').strip()
    parsed = urlsplit(raw)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise HTTPException(503, 'A public HTTPS portal origin must be configured')
    if parsed.hostname in ('localhost', '127.0.0.1'):
        raise HTTPException(503, 'A publicly reachable HTTPS origin is required')
    return raw.rstrip('/')


def _smtp_ready(sender):
    from app.services.moses_email_transport import ready
    return ready(sender)


def _path(request, platform):
    return location(request, platform, 'estimates_invoices').parent / 'moses_estimate_delivery_actions.json'


@contextmanager
def _locked(path: Path):
    lock_path = path.with_suffix('.lock')
    with open(lock_path, 'a+b') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'admin') if isinstance(user, dict) else str(user)


def _snapshot(request, platform, record_id):
    _guard(request, platform)
    _origin()
    record = _find_record(request, platform, 'estimate', record_id)
    number, total = acceptance._eligible(record)
    if not str(record.get('customer') or '').strip():
        raise HTTPException(409, 'Estimate customer must be reviewed')
    # Strictly use the estimate's verified job/customer contact; no invoice AP routing here.
    raw_recipient = str(record.get('contact_email') or record.get('customer_email') or record.get('email') or '').strip()
    recipient = _email(raw_recipient)
    if not recipient or '\n' in raw_recipient or '\r' in raw_recipient:
        raise HTTPException(409, 'Verify the estimate customer contact email before sending')
    sender = _email(os.getenv('MOSES_DOCUMENTS_FROM'))
    reply_to = _email(os.getenv('MOSES_ESTIMATES_REPLY_TO'))
    raw_cc = str(os.getenv('MOSES_ESTIMATES_CC') or '').strip()
    cc = _email(raw_cc) if raw_cc else ''
    if not sender or not reply_to or (raw_cc and not cc):
        raise HTTPException(409, 'Estimate sender, reply address, or CC is not configured')
    # Early preflight validates the PDF line items, tax and declared total.
    acceptance._pdf_lines(record)
    return {'platform': platform, 'record_id': record_id, 'number': number,
            'total': total, 'to': recipient, 'from': sender, 'reply_to': reply_to,
            'cc': cc, 'document_fingerprint': acceptance._fingerprint(record),
            'subject': 'Estimate ' + number,
            'portal_origin': _origin()}


def _fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def _public(row):
    snap = row['snapshot']
    return {'id': row['id'], 'state': row['state'], 'platform': row['platform'],
            'record_id': row['record_id'], 'to': snap['to'], 'from': snap['from'],
            'reply_to': snap['reply_to'], 'cc': snap['cc'], 'subject': snap['subject'],
            'document_number': snap['number'], 'total': snap['total'],
            'attachment_filename': snap['number'] + '.pdf',
            'requested_at': row['requested_at'], 'approval_required': row['state'] == 'pending',
            'sent': row['state'] == 'sent', 'transport': row.get('transport'),
            'delivery_status': row.get('delivery_status'),
            'provider_message_id': row.get('provider_message_id')}


def propose(request, platform, record_id):
    snap = _snapshot(request, platform, record_id)
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        if any(r.get('record_id') == record_id and r.get('state') in ('sending', 'uncertain') for r in rows):
            raise HTTPException(409, 'Prior estimate email outcome requires review before another send')
        fp = _fingerprint(snap)
        matching = next((r for r in rows if r['fingerprint'] == fp and r['state'] in ('pending', 'sent')), None)
        if matching:
            if matching['state'] == 'sent':
                raise HTTPException(409, 'This estimate was already emailed; review delivery history')
            return {'proposal': _public(matching), 'sent': False, 'approval_required': True}
        row = {'id': uuid.uuid4().hex, 'platform': platform, 'record_id': record_id,
               'fingerprint': fp, 'snapshot': snap, 'state': 'pending',
               'requested_at': _now(), 'requested_by': _actor(request)}
        rows.append(row)
        save(path, rows)
        return {'proposal': _public(row), 'sent': False, 'approval_required': True}


def decide(request, platform, proposal_id, approve):
    _guard(request, platform)
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        row = next((r for r in rows if r.get('id') == proposal_id and r.get('platform') == platform), None)
        if not row:
            raise HTTPException(404, 'Estimate email proposal not found')
        if row['state'] != 'pending':
            raise HTTPException(409, 'Estimate email proposal already processed')
        if not approve:
            row.update(state='rejected', decided_at=_now(), decided_by=_actor(request))
            save(path, rows)
            return {'state': 'rejected', 'sent': False, 'proposal_id': proposal_id}
        try:
            fresh = _snapshot(request, platform, row['record_id'])
        except HTTPException as exc:
            if exc.status_code in (404, 409):
                row.update(state='stale', decided_at=_now())
                save(path, rows)
            raise
        if _fingerprint(fresh) != row['fingerprint']:
            row.update(state='stale', decided_at=_now()); save(path, rows)
            raise HTTPException(409, 'Estimate or recipient changed; review a new proposal')
        _smtp_ready(fresh['from'])
        # Existing active acceptance links cannot be recovered from hashes. Revoke them
        # deliberately before sending, otherwise a second live link might be created.
        links = acceptance.history(request, platform, row['record_id'])
        if any(item['state'] == 'active' for item in links):
            raise HTTPException(409, 'Existing acceptance link must be revoked before email delivery')
        # Persist intent BEFORE creating a link or attempting SMTP. A server crash
        # here leaves an uncertain hold and cannot automatically send twice.
        row.update(state='sending', decided_at=_now(), decided_by=_actor(request))
        save(path, rows)
        try:
            link = acceptance.issue(request, platform, row['record_id'])
            pdf = acceptance.document_pdf(request, link['token'])
            url = fresh['portal_origin'] + link['acceptance_path']
            mail = dict(fresh)
            mail['text'] = ('Please review the attached estimate ' + fresh['number'] + '.\n\n'
                            'Review and accept your proposal securely:\n' + url + '\n\n'
                            'Please reply with any questions.')
            receipt_id = _transmit(mail, pdf)
            from app.services.moses_email_transport import delivery_receipt
            receipt = delivery_receipt(receipt_id)
        except Exception:
            row.update(state='uncertain', completed_at=_now())
            save(path, rows)
            return {'state': 'uncertain', 'sent': False, 'proposal_id': proposal_id,
                    'message': 'Delivery not confirmed. Inspect SMTP and acceptance history before retrying.'}
        # Never persist the bearer token or full URL in delivery records.
        row.update(state='sent', completed_at=_now(), acceptance_link_id=link['link_id'], **receipt)
        save(path, rows)
        return {'state': 'sent', 'sent': True, 'proposal_id': proposal_id,
                'recipient': fresh['to'], 'document_number': fresh['number']}


def history(request, platform, record_id):
    _guard(request, platform)
    return [_public(r) for r in load(_path(request, platform)) if r.get('record_id') == record_id][-50:]
