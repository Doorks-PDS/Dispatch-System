"""Opt-in, two-step dispatch email sending. No timers or automatic sends.

An SMTP timeout may mean the provider accepted mail: preserve 'uncertain' and
never automatically retry. Proposals are workspace-scoped and snapshot-bound.
"""
from __future__ import annotations

import hashlib
import json
import os
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from threading import RLock
from fastapi import HTTPException
from app.services.moses_delivery import preview_dispatch_eta

_LOCK = RLock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(request, platform):
    if platform not in ('doorks', 'pds'):
        raise HTTPException(400, 'Unsupported dispatch workspace')
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != platform or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active workspace office admin required')
    if os.environ.get('MOSES_DISPATCH_SEND_ENABLED', '').lower().strip() != 'true':
        raise HTTPException(503, 'Dispatch email sending is disabled')


def _path(request, platform):
    base = Path(request.app.state.data_dir)
    target = (base / 'moses_pds' if platform == 'pds' else base / 'business_workspaces' / 'doorks')
    target.mkdir(parents=True, exist_ok=True)
    return target / 'moses_dispatch_email_actions.json'


def _read(path):
    from app.routers.workspaces import load
    return load(path)


def _write(path, rows):
    from app.routers.workspaces import save
    save(path, rows)


def _fingerprint(message):
    fields = ('record_id', 'job_number', 'mode', 'scheduled_date', 'eta_time', 'to', 'from', 'reply_to', 'cc', 'subject', 'text')
    return hashlib.sha256(json.dumps({k: message.get(k) for k in fields}, sort_keys=True).encode()).hexdigest()


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else str(user)


def _prepare(request, platform, record_id, mode, eta_time, note):
    item = preview_dispatch_eta(request, platform, record_id, mode, eta_time, note)
    blockers = [issue for issue in item['issues'] if issue != 'Approved outbound email transport not enabled']
    if blockers:
        raise HTTPException(409, '; '.join(blockers))
    if not all(item.get(k) for k in ('to', 'from', 'reply_to', 'subject', 'text')):
        raise HTTPException(409, 'Missing verified email fields')
    return item


def propose(request, platform, record_id, mode, eta_time='', note=''):
    _guard(request, platform)
    message = _prepare(request, platform, record_id, mode, eta_time, note)
    key = _fingerprint(message)
    with _LOCK:
        path = _path(request, platform)
        rows = _read(path)
        existing = next((r for r in rows if r.get('fingerprint') == key and r.get('state') in ('pending','sending','sent','uncertain')), None)
        if existing:
            if existing['state'] == 'pending':
                return {'proposal': _public(existing), 'approval_required': True, 'executed': False}
            raise HTTPException(409, 'An identical message was already sent or may be in progress. Review delivery history.')
        row = {'id': uuid.uuid4().hex, 'platform': platform, 'record_id': record_id,
               'mode': mode, 'eta_time': eta_time, 'note': note,
               'fingerprint': key, 'message': {k: message.get(k) for k in ('to','from','reply_to','cc','subject','text')},
               'state': 'pending', 'requested_by': _actor(request), 'requested_at': _now()}
        rows.append(row)
        _write(path, rows)
        return {'proposal': _public(row), 'approval_required': True, 'executed': False}


def _public(row):
    return {k: row[k] for k in ('id','platform','record_id','mode','state','requested_at') if k in row} | {
        'to': row['message']['to'], 'subject': row['message']['subject'], 'text': row['message']['text'],
        'transport': row.get('transport'), 'delivery_status': row.get('delivery_status'),
        'provider_message_id': row.get('provider_message_id')}


def _transmit(message):
    from app.services.moses_email_transport import provider, send_resend
    if provider() == 'resend':
        return send_resend(message)
    host = os.environ.get('DOORKS_SMTP_HOST','').strip()
    username = os.environ.get('DOORKS_SMTP_USERNAME','').strip()
    password = os.environ.get('DOORKS_SMTP_PASSWORD','')
    sender = os.environ.get('DOORKS_SMTP_FROM','').strip()
    if not all((host, username, password, sender)) or sender.lower() != message['from'].lower():
        raise HTTPException(503, 'SMTP sender configuration unavailable or does not match verified From address')
    try:
        port = int(os.environ.get('DOORKS_SMTP_PORT', '465'))
    except ValueError:
        raise HTTPException(503, 'Invalid SMTP port')
    if not 1 <= port <= 65535:
        raise HTTPException(503, 'Invalid SMTP port')
    mail = EmailMessage()
    for header, key in (('From','from'),('To','to'),('Reply-To','reply_to'),('Subject','subject')):
        val = message[key]
        if '\r' in val or '\n' in val:
            raise HTTPException(422, 'Invalid email header')
        mail[header] = val
    if message.get('cc'):
        if '\r' in message['cc'] or '\n' in message['cc']:
            raise HTTPException(422, 'Invalid CC')
        mail['Cc'] = message['cc']
    mail.set_content(message['text'])
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
            smtp.login(username, password)
            smtp.send_message(mail)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(mail)


def decide(request, platform, proposal_id, approve):
    _guard(request, platform)
    with _LOCK:
        path = _path(request, platform)
        rows = _read(path)
        row = next((r for r in rows if r.get('id') == proposal_id and r.get('platform') == platform), None)
        if row is None:
            raise HTTPException(404, 'Email proposal not found')
        if row['state'] != 'pending':
            raise HTTPException(409, 'Proposal already processed; do not resend')
        if not approve:
            row.update(state='rejected', decided_by=_actor(request), decided_at=_now())
            _write(path, rows)
            return {'state': 'rejected', 'sent': False, 'proposal_id': proposal_id}
        # Re-read the job to catch changed recipients, dates or content before sending.
        current = _prepare(request, platform, row['record_id'], row['mode'], row['eta_time'], row['note'])
        if _fingerprint(current) != row['fingerprint']:
            row.update(state='stale', decided_at=_now())
            _write(path, rows)
            raise HTTPException(409, 'Job details or email recipient changed. Prepare a new email proposal.')
        # Validate sender before marking sending; no external side effect yet.
        from app.services.moses_email_transport import ready
        ready(current['from'])
        row.update(state='sending', decided_by=_actor(request), decided_at=_now())
        _write(path, rows)
        # No retries: unknown SMTP acknowledgment can mean the message was delivered.
        try:
            receipt_id = _transmit(row['message'])
            from app.services.moses_email_transport import delivery_receipt
            receipt = delivery_receipt(receipt_id)
        except Exception:
            row.update(state='uncertain', completed_at=_now())
            _write(path, rows)
            return {'state': 'uncertain', 'sent': False, 'proposal_id': proposal_id,
                    'message': 'Delivery not confirmed. Check the provider before considering a new message.'}
        row.update(state='sent', completed_at=_now(), **receipt)
        _write(path, rows)
        return {'state': 'sent', 'sent': True, 'proposal_id': proposal_id,
                'recipient': row['message']['to']}


def history(request, platform, record_id):
    _guard(request, platform)
    return [_public(r) for r in _read(_path(request, platform)) if r['record_id'] == record_id][-50:]
