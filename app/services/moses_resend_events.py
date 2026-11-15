"""Signed Resend delivery observations (not new send requests).

The webhook stores only event IDs, provider email IDs and delivery states. Events
are not allowed to authorize retries or mutate invoices, proposals or jobs.
"""
from __future__ import annotations

import base64
import binascii
import fcntl
import hashlib
import hmac
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from app.routers.workspaces import load, save

EVENT_STATES = {
    'email.sent': 'sent_by_provider',
    'email.delivered': 'delivered_to_recipient_server',
    'email.delivery_delayed': 'delivery_delayed',
    'email.bounced': 'bounced',
    'email.complained': 'spam_complaint',
    'email.failed': 'failed',
    'email.suppressed': 'suppressed',
}


def _ledger(request, *, create=False):
    target = Path(request.app.state.data_dir) / 'moses_resend_delivery_events.json'
    if create:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


@contextmanager
def _locked(path):
    with open(path.with_suffix('.lock'), 'a+b') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def verify(body: bytes, headers, now=None):
    secret = os.getenv('RESEND_WEBHOOK_SECRET', '').strip()
    if not secret.startswith('whsec_'):
        raise HTTPException(503, 'Resend delivery events not configured')
    if len(body) > 65536:
        raise HTTPException(413, 'Webhook payload too large')
    msg_id = headers.get('svix-id', '')
    timestamp = headers.get('svix-timestamp', '')
    signature = headers.get('svix-signature', '')
    if (not msg_id or len(msg_id) > 200 or not timestamp.isascii()
            or not timestamp.isdecimal() or len(timestamp) > 12
            or not isinstance(signature, str) or len(signature) > 4096):
        raise HTTPException(400, 'Missing or invalid webhook signature headers')
    if abs(int(timestamp) - (time.time() if now is None else now)) > 300:
        raise HTTPException(400, 'Stale webhook timestamp')
    try:
        signing_key = base64.b64decode(secret[6:] + '===', validate=False)
        signed = msg_id.encode() + b'.' + timestamp.encode() + b'.' + body
        expected = hmac.new(signing_key, signed, hashlib.sha256).digest()
        parts = signature.split(' ')
        valid = any(part.startswith('v1,') and hmac.compare_digest(
            expected, base64.b64decode(part[3:] + '=' * (-len(part[3:]) % 4), validate=True))
            for part in parts)
    except (ValueError, TypeError, binascii.Error):
        valid = False
    if not valid:
        raise HTTPException(400, 'Invalid Resend webhook signature')
    try:
        event = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, 'Invalid webhook payload')
    if not isinstance(event, dict):
        raise HTTPException(400, 'Invalid webhook event')
    return msg_id, event


def receive(request, body: bytes):
    event_id, event = verify(body, request.headers)
    event_type = event.get('type')
    if event_type not in EVENT_STATES:
        return {'received': True, 'tracked': False}
    data = event.get('data')
    email_id = data.get('email_id') if isinstance(data, dict) else None
    if not isinstance(email_id, str) or not 1 <= len(email_id) <= 256 or not all(c.isalnum() or c in '_-' for c in email_id):
        raise HTTPException(400, 'Invalid provider email reference')
    # Limit stored metadata: never persist addresses, subjects, bodies or links.
    created_at = str(event.get('created_at') or '')
    try:
        occurred = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if occurred.tzinfo is None:
            raise ValueError('missing zone')
        when = occurred.astimezone(timezone.utc).isoformat()
    except ValueError:
        raise HTTPException(400, 'Invalid event timestamp')
    path = _ledger(request, create=True)
    with _locked(path):
        rows = load(path)
        if any(row['event_id'] == event_id for row in rows):
            return {'received': True, 'tracked': True, 'duplicate': True}
        rows.append({'event_id': event_id, 'provider_message_id': email_id,
                     'delivery_status': EVENT_STATES[event_type], 'occurred_at': when})
        save(path, rows)
    return {'received': True, 'tracked': True, 'duplicate': False}


def _action_file(request, platform, kind):
    base = Path(request.app.state.data_dir)
    folder = base / 'moses_pds' if platform == 'pds' else base / 'business_workspaces' / platform
    name = {
        'dispatch': 'moses_dispatch_email_actions.json',
        'purchase_order': 'moses_po_delivery_actions.json',
        'estimate': 'moses_estimate_delivery_actions.json',
        'invoice': 'moses_invoice_delivery_actions.json',
    }[kind]
    return folder / name


def status(request, platform, kind, record_id):
    if platform not in ('pds', 'doorks', 'sdc') or kind not in ('dispatch', 'purchase_order', 'estimate', 'invoice'):
        raise HTTPException(404, 'Unknown delivery history')
    if platform == 'sdc' and kind == 'dispatch' or platform == 'pds' and kind in ('estimate','invoice'):
        raise HTTPException(404, 'No such delivery history in this workspace')
    if (not getattr(request.state, 'auth_user', None) or
        getattr(request.state, 'auth_role', None) != 'office_admin' or
        request.session.get('active_platform') != platform):
        raise HTTPException(403, 'Active workspace office administrator required')
    actions_path = _action_file(request, platform, kind)
    actions = load(actions_path) if actions_path.exists() else []
    relevant = [a for a in actions if str(a.get('record_id')) == record_id]
    ledger = _ledger(request)
    if ledger.exists():
        with _locked(ledger):
            events = load(ledger)
    else:
        events = []
    result = []
    for row in relevant[-50:]:
        provider_id = row.get('provider_message_id')
        matching = sorted((e for e in events if e['provider_message_id'] == provider_id),
                          key=lambda e: (e['occurred_at'], e['event_id'])) if provider_id else []
        latest = matching[-1] if matching else None
        result.append({'proposal_id': row.get('id'), 'state': row.get('state'),
                       'provider_message_id': provider_id,
                       'delivery_status': (latest or row).get('delivery_status') or 'not_confirmed',
                       'delivery_event_at': latest['occurred_at'] if latest else None})
    return {'items': result}
