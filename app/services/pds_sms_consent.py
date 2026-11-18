"""PDS text-keyword consent ledger. All data lives under app.state.data_dir.

Provision app.state.data_dir on a DURABLE Render disk before accepting messages.
No outbound service is authorized to bypass can_send().
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

NUMBER = os.getenv('PDS_TWILIO_NUMBER', '+17606421131').strip()
HELP_PHONE = os.getenv('PDS_SMS_HELP_PHONE', '(760) 233-5037').strip()


def normalize_number(raw: str) -> str:
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 10:
        digits = '1' + digits
    if len(digits) != 11 or not digits.startswith('1'):
        raise ValueError('Expected a US phone number')
    return '+' + digits


@contextmanager
def _connect(data_dir):
    path = Path(data_dir) / 'pds_sms' / 'consent.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_consent (
        phone TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'unknown',
        updated_at TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'keyword')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_events (
        message_sid TEXT PRIMARY KEY, phone TEXT NOT NULL, keyword TEXT NOT NULL,
        created_at TEXT NOT NULL, resulting_state TEXT NOT NULL, response TEXT NOT NULL)''')
    conn.commit()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def current_state(data_dir, phone: str) -> str:
    normalized = normalize_number(phone)
    with _connect(data_dir) as db:
        row = db.execute('SELECT state FROM sms_consent WHERE phone=?', (normalized,)).fetchone()
        return row['state'] if row else 'unknown'


def can_send(data_dir, phone: str) -> bool:
    return current_state(data_dir, phone) == 'subscribed'


def handle_keyword(data_dir, phone: str, message_sid: str, body: str, *, privacy_url: str, terms_url: str):
    """Return (response, state), atomically storing/replaying the webhook SID.

    STOP/START are deliberately handled before message eligibility checks.
    Twilio's built-in opt-out (if enabled) must remain authoritative as well.
    """
    phone = normalize_number(phone)
    if not message_sid or len(message_sid) > 128:
        raise ValueError('Valid message SID required')
    keyword = (body or '').strip().upper().split()[0] if (body or '').strip() else ''
    now = datetime.now(timezone.utc).isoformat()
    with _connect(data_dir) as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT response, resulting_state FROM sms_events WHERE message_sid=?', (message_sid,)).fetchone()
        if previous:
            return previous['response'], previous['resulting_state']
        row = db.execute('SELECT state FROM sms_consent WHERE phone=?', (phone,)).fetchone()
        state = row['state'] if row else 'unknown'
        result = state
        if keyword == 'START':
            result = 'pending'
            reply = (f'Priority Door Systems: Reply YES to confirm service text updates '
                     f'(appointments, technician ETAs, job status). Msg frequency varies; '
                     f'msg & data rates may apply. STOP to opt out; HELP for help. '
                     f'Privacy: {privacy_url} Terms: {terms_url}')
        elif keyword in ('YES', 'Y'):
            if state == 'pending':
                result = 'subscribed'
                reply = ('Priority Door Systems: You are subscribed to service updates. '
                         'Message frequency varies. Msg & data rates may apply. '
                         'Reply STOP to opt out or HELP for help.')
            else:
                reply = 'Priority Door Systems: To subscribe, first text START, then reply YES.'
        elif keyword in ('STOP', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT', 'STOPALL', 'REVOKE', 'OPTOUT'):
            result = 'unsubscribed'
            reply = 'Priority Door Systems: You are unsubscribed and will not receive further service texts. Text START to rejoin.'
        elif keyword in ('HELP', 'INFO'):
            reply = (f'Priority Door Systems service updates. For support call {HELP_PHONE}. '
                     'Text START to subscribe or STOP to unsubscribe. Msg & data rates may apply.')
        else:
            reply = ('Priority Door Systems: Text START to request service updates, '
                     'YES to confirm an existing request, HELP for assistance, or STOP to opt out.')
        if result != state:
            db.execute('''INSERT INTO sms_consent(phone,state,updated_at,origin) VALUES (?,?,?,?)
                ON CONFLICT(phone) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at''',
                (phone, result, now, 'keyword'))
        db.execute('INSERT INTO sms_events VALUES (?,?,?,?,?,?)',
                   (message_sid, phone, keyword[:60], now, result, reply))
        db.commit()
        return reply, result
