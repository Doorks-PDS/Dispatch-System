"""Explicitly approved PDS schedule emails. Preview/proposal never sends.

No job update here: the Scheduler remains the single scheduling authority.
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
from app.services.moses_delivery import _email
from app.services.moses_email_transport import ready

CATEGORIES = {'appointment', 'schedule_change', 'eta', 'custom'}

def _now():
    return datetime.now(timezone.utc).isoformat()

def _guard(request):
    if (not getattr(request.state, 'auth_user', None) or
        request.session.get('active_platform') != 'pds' or
        getattr(request.state, 'auth_role', None) != 'office_admin'):
        raise HTTPException(403, 'PDS office-admin access required')

@contextmanager
def _db(request):
    path=Path(request.app.state.data_dir)/'pds_schedule_notifications'
    path.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(path/'approvals.sqlite3'),timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS proposals (
      id TEXT PRIMARY KEY,job_id TEXT NOT NULL,recipient TEXT NOT NULL,
      category TEXT NOT NULL,subject TEXT NOT NULL,message TEXT NOT NULL,
      status TEXT NOT NULL,created_at TEXT NOT NULL,decided_at TEXT,
      provider_id TEXT,actor TEXT NOT NULL,last_error TEXT)''')
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()

def _job(request,job_id):
    if not isinstance(job_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',job_id):
        raise HTTPException(422,'Exact internal job ID required')
    item=request.app.state.calendar_store.get_job(job_id)
    if not isinstance(item,dict) or str(item.get('id'))!=job_id:
        raise HTTPException(404,'Saved PDS job not found')
    return item

def _verified_email(job,recipient):
    email=_email(recipient)
    if not email:
        raise HTTPException(422,'Valid customer email required')
    known={_email(job.get(field)) for field in ('email','contact_email','customer_email')}
    if email not in known:
        raise HTTPException(409,'Recipient email does not match the saved job')
    return email

def email_readiness(request):
    """Check live configured email gates without contacting Resend or exposing secrets."""
    _guard(request)
    sender = os.getenv('MOSES_DOCUMENTS_FROM', '').strip()
    reply = os.getenv('PDS_GENERAL_REPLY_TO', 'reception@prioritydoors.com').strip()
    issues = []
    if os.getenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED', '').strip().lower() != 'true':
        issues.append('Customer schedule emails are disabled in Render.')
    if os.getenv('MOSES_EMAIL_PROVIDER', '').strip().lower() != 'resend':
        issues.append('Resend is not selected as the email provider.')
    if not os.getenv('RESEND_API_KEY', '').startswith('re_'):
        issues.append('Resend API key is not configured.')
    if not _email(sender):
        issues.append('Company sender is not configured (MOSES_DOCUMENTS_FROM).')
    if not _email(reply):
        issues.append('Customer Reply-To address is invalid.')
    return {'enabled': not issues, 'from': sender, 'reply_to': reply, 'issues': issues}


def propose(request,job_id,recipient,category,subject,message):
    _guard(request)
    job=_job(request,job_id)
    recipient=_verified_email(job,recipient)
    category=str(category or '').strip()
    if category not in CATEGORIES:
        raise HTTPException(422,'Unsupported notification category')
    subject=str(subject or '').strip()
    message=str(message or '').strip()
    if not 1<=len(subject)<=140 or not 1<=len(message)<=1600 or any(ch in subject for ch in '\r\n\0') or '\0' in message:
        raise HTTPException(422,'Invalid notification subject or message')
    if not message.startswith('Priority Door Systems:'):
        raise HTTPException(422,'Message must identify Priority Door Systems')
    actor=request.state.auth_user
    actor=str(actor.get('id') or actor.get('username') or 'office_admin') if isinstance(actor,dict) else 'office_admin'
    pid=uuid.uuid4().hex
    with _db(request) as db:
        # Serialize proposal creation so two office clicks cannot create two
        # independently approvable copies of the same pending notification.
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute(
            """SELECT id FROM proposals WHERE job_id=? AND recipient=? AND category=?
               AND subject=? AND message=? AND status='pending'
               ORDER BY created_at ASC LIMIT 1""",
            (job_id, recipient, category, subject, message),
        ).fetchone()
        if existing:
            pid = existing['id']
            reused = True
        else:
            db.execute('INSERT INTO proposals (id,job_id,recipient,category,subject,message,status,created_at,actor) VALUES (?,?,?,?,?,?,?,?,?)',
                       (pid,job_id,recipient,category,subject,message,'pending',_now(),actor))
            reused = False
        db.commit()
    return {'proposal':{'id':pid,'job_id':job_id,'recipient':recipient,'status':'pending','subject':subject,'message':message},
            'reused_pending':reused,'sent':False,'approval_required':True}

def history(request,job_id):
    _guard(request)
    _job(request,job_id)
    with _db(request) as db:
        items=db.execute('SELECT id,job_id,recipient,category,subject,message,status,created_at,decided_at,provider_id,actor FROM proposals WHERE job_id=? ORDER BY created_at DESC LIMIT 100',(job_id,)).fetchall()
    return {'items':[dict(item) for item in items]}

def decide(request,pid,approve):
    _guard(request)
    if not re.fullmatch('[a-f0-9]{32}',pid or '') or not isinstance(approve,bool):
        raise HTTPException(422,'Invalid decision')
    with _db(request) as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM proposals WHERE id=?',(pid,)).fetchone()
        if not row:raise HTTPException(404,'Proposal not found')
        if row['status']!='pending':raise HTTPException(409,'Already decided or needs manual review')
        if not approve:
            db.execute("UPDATE proposals SET status='rejected',decided_at=? WHERE id=?",(_now(),pid))
            db.commit()
            return {'id':pid,'status':'rejected','sent':False}
        if os.getenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED','').lower()!='true':
            raise HTTPException(503,'Schedule emails disabled')
        job=_job(request,row['job_id'])
        _verified_email(job,row['recipient'])
        sender=os.getenv('MOSES_DOCUMENTS_FROM','').strip()
        ready(sender)
        db.execute("UPDATE proposals SET status='needs_review',decided_at=? WHERE id=?",(_now(),pid))
        db.commit()
    message={'from':sender,'to':row['recipient'],'reply_to':os.getenv('PDS_GENERAL_REPLY_TO','reception@prioritydoors.com'),
             'subject':row['subject'],'text':row['message']}
    # Reuse Resend's shared provider approval transport, but no fake document attachment.
    from app.services.moses_email_transport import send_resend
    try:
        provider_id=send_resend(message)
    except Exception as exc:
        with _db(request) as db:
            db.execute('UPDATE proposals SET last_error=? WHERE id=?',(type(exc).__name__[:80],pid))
        raise HTTPException(502,'Email outcome uncertain; check Resend before retrying') from exc
    with _db(request) as db:
        db.execute("UPDATE proposals SET status='submitted',provider_id=? WHERE id=? AND status='needs_review'",(str(provider_id),pid))
    return {'id':pid,'status':'submitted','provider_id':provider_id,'delivered':False}
