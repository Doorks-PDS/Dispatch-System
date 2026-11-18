"""Approval-gated PDS service texts; never send from an agent tool directly.

The durable consent ledger is authoritative in addition to Twilio's carrier opt-out.
Ambiguous sends are NOT retried automatically. Only an office admin approves sends.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from app.services.pds_sms_consent import normalize_number, can_send

MAX_LENGTH = 320

def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(request):
    if (not getattr(request.state, 'auth_user', None) or
            request.session.get('active_platform') != 'pds' or
            getattr(request.state, 'auth_role', None) != 'office_admin'):
        raise HTTPException(403, 'PDS office-admin access required')


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else str(user)


@contextmanager
def _db(request):
    base = Path(request.app.state.data_dir) / 'pds_sms'
    base.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(base / 'send_approvals.sqlite3'), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS proposals (
        id TEXT PRIMARY KEY, phone TEXT NOT NULL, message TEXT NOT NULL,
        job_id TEXT NOT NULL, status TEXT NOT NULL, actor TEXT NOT NULL,
        created_at TEXT NOT NULL, decided_at TEXT, provider_sid TEXT,
        last_error TEXT)''')
    conn.commit()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _public(row):
    return dict(row) if row else None


def _job(request, job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
        raise HTTPException(422, 'Exact PDS internal job ID required')
    record = request.app.state.calendar_store.get_job(job_id)
    if not isinstance(record, dict) or str(record.get('id')) != job_id:
        raise HTTPException(404, 'Verified PDS job not found')
    return record


def _verified_job_phone(job, phone):
    """Recheck recipient against the current saved job before approval/send."""
    try:
        normalized = normalize_number(phone)
    except ValueError as exc:
        raise HTTPException(422, 'US mobile number required') from exc
    saved = set()
    for key in ('phone', 'contact_phone', 'customer_phone', 'mobile'):
        try:
            saved.add(normalize_number(str(job.get(key) or '')))
        except ValueError:
            continue
    if normalized not in saved:
        raise HTTPException(409, 'Recipient phone is not verified on the PDS job')
    return normalized


def propose(request, job_id, phone, message):
    _guard(request)
    job = _job(request, job_id)
    normalized = _verified_job_phone(job, phone)
    message = str(message or '').strip()
    if not 1 <= len(message) <= MAX_LENGTH or any(c in message for c in ('\x00', '\r')):
        raise HTTPException(422, 'Service text must be between 1 and 320 characters')
    if not message.startswith('Priority Door Systems:'):
        raise HTTPException(422, 'Service text must identify Priority Door Systems')
    if not can_send(request.app.state.data_dir, normalized):
        raise HTTPException(409, 'Recipient has not confirmed SMS consent')
    pid = uuid.uuid4().hex
    with _db(request) as db:
        # A double-click must not produce two independently approvable SMS sends.
        # SQLite's immediate write lock makes this check atomic across workers.
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute(
            """SELECT id FROM proposals WHERE job_id=? AND phone=? AND message=?
               AND status='pending' ORDER BY created_at ASC LIMIT 1""",
            (job_id, normalized, message),
        ).fetchone()
        if existing:
            pid = existing['id']
            reused = True
        else:
            db.execute('INSERT INTO proposals (id,phone,message,job_id,status,actor,created_at) VALUES (?,?,?,?,?,?,?)',
                       (pid, normalized, message, job_id, 'pending', _actor(request), _now()))
            reused = False
        db.commit()
    return {'proposal': {'id':pid, 'job_id':job_id, 'phone':normalized, 'message':message,
                         'status':'pending'}, 'reused_pending':reused,
            'approval_required':True, 'sent':False}


def pending(request):
    _guard(request)
    with _db(request) as db:
        rows = db.execute("SELECT * FROM proposals WHERE status IN ('pending','needs_review') ORDER BY created_at DESC LIMIT 50").fetchall()
    return {'workspace':'pds', 'proposals':[_public(row) for row in rows], 'sent':False}


def job_history(request, job_id):
    """Recent saved notifications for this exact PDS job, including final states."""
    _guard(request)
    _job(request, job_id)
    with _db(request) as db:
        rows = db.execute('SELECT id,job_id,phone,message,status,actor,created_at,decided_at,provider_sid FROM proposals WHERE job_id=? ORDER BY created_at DESC LIMIT 100', (job_id,)).fetchall()
    return {'items': [_public(row) for row in rows]}


def receipt(request, pid):
    _guard(request)
    if not re.fullmatch('[a-f0-9]{32}', pid or ''):
        raise HTTPException(422, 'Invalid proposal ID')
    with _db(request) as db:
        row = db.execute('SELECT * FROM proposals WHERE id=?', (pid,)).fetchone()
    if not row:
        raise HTTPException(404, 'Proposal not found')
    result = _public(row)
    result['executed'] = result['status'] in ('submitted','delivered')
    return result


def decide(request, pid, approve):
    """POST-only human decision; never retry a possibly accepted provider send."""
    _guard(request)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Approval must be boolean')
    if not re.fullmatch('[a-f0-9]{32}', pid or ''):
        raise HTTPException(422, 'Invalid proposal ID')
    with _db(request) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM proposals WHERE id=?', (pid,)).fetchone()
        if not row:
            raise HTTPException(404, 'Proposal not found')
        if row['status'] != 'pending':
            raise HTTPException(409, 'Already decided or awaiting manual review')
        if not approve:
            db.execute("UPDATE proposals SET status='rejected',decided_at=? WHERE id=?", (_now(), pid))
            db.commit()
            return {'id':pid, 'status':'rejected', 'sent':False}
        if os.getenv('PDS_SMS_SEND_ENABLED', '').lower() != 'true':
            raise HTTPException(503, 'Outbound SMS disabled')
        current_job = _job(request, row['job_id'])
        _verified_job_phone(current_job, row['phone'])
        if not can_send(request.app.state.data_dir, row['phone']):
            raise HTTPException(409, 'SMS consent was revoked or is unavailable')
        token = os.getenv('TWILIO_AUTH_TOKEN', '')
        sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        sender = os.getenv('PDS_TWILIO_NUMBER', '')
        public_url = os.getenv('PDS_SMS_PUBLIC_BASE_URL', '').rstrip('/')
        if not token or not re.fullmatch(r'AC[a-fA-F0-9]{32}', sid) or not sender or not public_url.startswith('https://'):
            raise HTTPException(503, 'Twilio SMS provider or public callback URL not configured')
        # Persist irreversible intent before sending; crash/restart => needs_review.
        db.execute("UPDATE proposals SET status='needs_review',decided_at=? WHERE id=?", (_now(), pid))
        db.commit()
    try:
        import requests
        response = requests.post(
            f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',
            auth=(sid, token), data={'To':row['phone'], 'From':sender, 'Body':row['message'],
                  'StatusCallback':os.getenv('PDS_SMS_PUBLIC_BASE_URL','').rstrip('/') + '/pds/sms/twilio/status?proposal_id=' + pid},
            timeout=12)
        response.raise_for_status()
        payload = response.json()
        provider_sid = str(payload.get('sid') or '')
        if not provider_sid.startswith('SM'):
            raise RuntimeError('Twilio did not return a valid message SID')
    except Exception as exc:
        # This may have been accepted. Never resend automatically.
        with _db(request) as db:
            db.execute('UPDATE proposals SET last_error=? WHERE id=?',
                       (type(exc).__name__[:80], pid))
        raise HTTPException(502, 'SMS delivery outcome uncertain; review provider logs before retrying') from exc
    with _db(request) as db:
        # A signed status callback may have arrived before the API response.
        # Never downgrade a terminal provider outcome.
        db.execute("UPDATE proposals SET status='submitted',provider_sid=? "
                   "WHERE id=? AND status='needs_review' AND provider_sid IS NULL",
                   (provider_sid, pid))
        saved = db.execute('SELECT status,provider_sid FROM proposals WHERE id=?',
                           (pid,)).fetchone()
        if saved['provider_sid'] != provider_sid:
            raise HTTPException(409, 'Twilio callback and API response disagree; manual review required')
    return {'id':pid, 'status':saved['status'], 'provider_sid':provider_sid,
            'submitted':True, 'delivered':saved['status']=='delivered'}



def reconcile_status(data_dir, provider_sid, delivery_status, proposal_id=None):
    """Reconcile signed Twilio status callbacks; duplicate callbacks are harmless.

    Delivery status is not consent; opt-out must be handled independently.
    """
    if not isinstance(provider_sid,str) or not re.fullmatch(r'SM[a-fA-F0-9]{32}',provider_sid):
        raise ValueError('Invalid Twilio message SID')
    valid={'queued','accepted','sending','sent','delivered','undelivered','failed'}
    if delivery_status not in valid:raise ValueError('Invalid Twilio status')
    path=Path(data_dir)/'pds_sms'/'send_approvals.sqlite3'
    if not path.is_file():return False
    with sqlite3.connect(str(path),timeout=20) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT id,status,provider_sid FROM proposals WHERE provider_sid=?',(provider_sid,)).fetchone()
        if not row and proposal_id and re.fullmatch(r'[a-f0-9]{32}',proposal_id):
            # A signed callback may arrive before the API response is persisted.
            # Only attach it to the exact already-approved, in-flight proposal.
            candidate=db.execute('SELECT id,status,provider_sid FROM proposals WHERE id=?',
                                 (proposal_id,)).fetchone()
            if candidate and candidate['status']=='needs_review' and not candidate['provider_sid']:
                db.execute('UPDATE proposals SET provider_sid=? WHERE id=? AND provider_sid IS NULL',
                           (provider_sid,proposal_id))
                row=db.execute('SELECT id,status,provider_sid FROM proposals WHERE id=?',
                               (proposal_id,)).fetchone()
        if not row:return False
        if proposal_id and row['id'] != proposal_id:
            return False
        # Terminal provider decisions are never downgraded by out-of-order callbacks.
        current=row['status']
        if current in ('delivered','undelivered','failed'):
            return True
        next_status=delivery_status if delivery_status in ('delivered','undelivered','failed') else 'submitted'
        db.execute('UPDATE proposals SET status=? WHERE provider_sid=?',(next_status,provider_sid))
    return True
