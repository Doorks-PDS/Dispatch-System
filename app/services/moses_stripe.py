"""Opt-in Stripe TEST Checkout for workspace invoices; never changes PDS/QuickBooks.

The signed webhook reconciles a separate payment ledger. Invoice status changes and
customer emails are intentionally not automatic until cross-record accounting is tested.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request as URLRequest, urlopen
import fcntl
import hashlib
import hmac
import json
import os
import time
import uuid

from fastapi import HTTPException
from app.routers.workspaces import guard, location, load, save
from app.services.moses_delivery import _find_record, _invoice_recipient


def _now():
    return datetime.now(timezone.utc).isoformat()


def _enabled():
    if os.getenv('MOSES_STRIPE_TEST_ENABLED', '').lower() != 'true':
        raise HTTPException(503, 'Stripe test checkout is disabled')
    key = os.getenv('STRIPE_SECRET_KEY', '')
    if not key.startswith('sk_test_'):
        raise HTTPException(503, 'Only Stripe test-mode credentials are permitted')
    return key


def _admin(request, platform):
    if platform not in ('doorks', 'sdc'):
        raise HTTPException(404, 'Invoice Stripe checkout is not connected for this workspace')
    guard(request, platform, 'estimates_invoices')


def _path(request, platform):
    return location(request, platform, 'estimates_invoices').parent / 'moses_stripe_checkout.json'


@contextmanager
def _locked(path: Path):
    with open(path.with_suffix('.lock'), 'a+b') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _money(value):
    try:
        amount = Decimal(str(value))
        cents = amount * 100
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(409, 'Invoice total is invalid')
    if not amount.is_finite() or cents != cents.to_integral_value() or not 50 <= cents <= 99999999:
        raise HTTPException(409, 'Invoice amount must be positive USD with exact cents')
    return int(cents)


def _snapshot(request, platform, record_id):
    _admin(request, platform)
    invoice = _find_record(request, platform, 'invoice', record_id)
    if str(invoice.get('status') or '').strip().lower() not in ('sent', 'issued', 'open', 'unpaid'):
        raise HTTPException(409, 'Invoice must be finalized, unpaid, and not voided')
    number = str(invoice.get('document_number') or '').strip()
    if not number or len(number) > 80:
        raise HTTPException(409, 'Invoice number must be finalized')
    if invoice.get('pricing_required') or invoice.get('requires_number_assignment'):
        raise HTTPException(409, 'Invoice requires pricing or numbering review')
    recipient, source = _invoice_recipient(request, platform, invoice)
    if not recipient:
        raise HTTPException(409, 'Verify customer AP or job contact email')
    amount = _money(invoice.get('total', invoice.get('amount')))
    return {'platform': platform, 'record_id': record_id, 'number': number,
            'amount_cents': amount, 'currency': 'usd', 'recipient': recipient,
            'recipient_source': source}


def _fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def _origin():
    raw = os.getenv('MOSES_PUBLIC_BASE_URL', '').strip()
    url = urlsplit(raw)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment or url.hostname in ('localhost', '127.0.0.1'):
        raise HTTPException(503, 'A public HTTPS origin is required for Stripe checkout')
    return raw.rstrip('/')


def _public(row):
    snap = row['snapshot']
    return {'id': row['id'], 'state': row['state'], 'platform': row['platform'],
            'record_id': snap['record_id'], 'number': snap['number'],
            'amount_cents': snap['amount_cents'], 'currency': snap['currency'],
            'recipient': snap['recipient'], 'requested_at': row['requested_at'],
            'checkout_url': row.get('checkout_url') if row['state'] in ('checkout_ready', 'paid') else None,
            'paid_at': row.get('paid_at'), 'requires_approval': row['state'] == 'pending'}


def propose(request, platform, record_id):
    _enabled()
    snap = _snapshot(request, platform, record_id)
    _origin()
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        prior = next((r for r in rows if r['snapshot']['record_id'] == record_id and r['state'] in ('pending', 'creating', 'uncertain', 'checkout_ready', 'paid')), None)
        if prior:
            if prior['state'] == 'pending' and prior['fingerprint'] == _fingerprint(snap):
                return {'proposal': _public(prior)}
            raise HTTPException(409, 'An invoice checkout already exists or needs reconciliation')
        row = {'id': uuid.uuid4().hex, 'platform': platform, 'snapshot': snap,
               'fingerprint': _fingerprint(snap), 'state': 'pending', 'requested_at': _now()}
        rows.append(row)
        save(path, rows)
        return {'proposal': _public(row)}


def _stripe_create(key, row, origin):
    snap = row['snapshot']
    # TEST mode only. Do not place customer details in metadata or success URLs.
    fields = {
        'mode': 'payment', 'payment_method_types[0]': 'card',
        'line_items[0][price_data][currency]': 'usd',
        'line_items[0][price_data][unit_amount]': str(snap['amount_cents']),
        'line_items[0][price_data][product_data][name]': 'Invoice ' + snap['number'],
        'line_items[0][quantity]': '1', 'client_reference_id': row['id'],
        'customer_email': snap['recipient'],
        'success_url': origin + '/?payment=return',
        'cancel_url': origin + '/?payment=cancelled',
        'metadata[moses_checkout_id]': row['id'],
    }
    payload = urlencode(fields).encode()
    req = URLRequest('https://api.stripe.com/v1/checkout/sessions', payload,
                     {'Authorization': 'Bearer ' + key,
                      'Content-Type': 'application/x-www-form-urlencoded',
                      'Idempotency-Key': 'moses-' + row['id']}, method='POST')
    with urlopen(req, timeout=15) as response:
        return json.loads(response.read(100000))


def decide(request, platform, proposal_id, approve):
    key = _enabled()
    _admin(request, platform)
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        row = next((r for r in rows if r['id'] == proposal_id and r['platform'] == platform), None)
        if not row:
            raise HTTPException(404, 'Checkout proposal not found')
        if row['state'] != 'pending':
            raise HTTPException(409, 'Checkout proposal already processed')
        if not approve:
            row['state'] = 'rejected'; row['decided_at'] = _now()
            save(path, rows)
            return {'state': 'rejected', 'payment_created': False}
        try:
            snap = _snapshot(request, platform, row['snapshot']['record_id'])
        except HTTPException:
            row['state'] = 'stale'; save(path, rows)
            raise
        if _fingerprint(snap) != row['fingerprint']:
            row['state'] = 'stale'; save(path, rows)
            raise HTTPException(409, 'Invoice, amount, or recipient changed')
        origin = _origin()
        # Persist intent first; an ambiguous provider response must never create
        # an untracked second Checkout session.
        row['state'] = 'creating'; row['decided_at'] = _now()
        save(path, rows)
        try:
            session = _stripe_create(key, row, origin)
            sid, url = session['id'], session['url']
            if (not sid.startswith('cs_test_') or urlsplit(url).scheme != 'https'
                    or urlsplit(url).hostname not in ('checkout.stripe.com', 'checkout.stripe.dev')
                    or session.get('mode') != 'payment' or session.get('currency') != 'usd'
                    or session.get('amount_total') != snap['amount_cents']):
                raise ValueError('Stripe Checkout returned mismatched session')
        except Exception:
            row['state'] = 'uncertain'; row['completed_at'] = _now()
            save(path, rows)
            return {'state': 'uncertain', 'payment_created': False,
                    'message': 'Verify Stripe dashboard before retrying checkout creation'}
        row.update(state='checkout_ready', stripe_session_id=sid, checkout_url=url, completed_at=_now())
        save(path, rows)
        return {'state': 'checkout_ready', 'payment_created': False,
                'checkout_url': url, 'proposal_id': row['id']}


def verify_signature(body: bytes, header: str, secret: str, now=None):
    if not secret or len(body) > 500000:
        raise HTTPException(400, 'Invalid Stripe event')
    pairs = [part.strip().split('=', 1) for part in header.split(',') if '=' in part]
    timestamps = [v for k, v in pairs if k == 't']
    signatures = [v for k, v in pairs if k == 'v1']
    if len(timestamps) != 1 or not signatures:
        raise HTTPException(400, 'Missing Stripe signature')
    try:
        timestamp = int(timestamps[0])
    except ValueError:
        raise HTTPException(400, 'Invalid Stripe signature timestamp')
    if abs((time.time() if now is None else now) - timestamp) > 300:
        raise HTTPException(400, 'Stripe webhook timestamp expired')
    expected = hmac.new(secret.encode(), str(timestamp).encode() + b'.' + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise HTTPException(400, 'Invalid Stripe signature')
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, 'Malformed Stripe event')


def webhook(request, body, signature):
    # Test mode only. Public endpoint, but every event is authenticated via HMAC.
    _enabled()
    event = verify_signature(body, signature, os.getenv('STRIPE_WEBHOOK_SECRET', ''))
    if event.get('livemode') is not False:
        raise HTTPException(400, 'Live Stripe events are not enabled')
    if event.get('type') not in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        return {'received': True, 'processed': False}
    session = event.get('data', {}).get('object', {})
    if session.get('payment_status') != 'paid':
        return {'received': True, 'processed': False}
    sid = str(session.get('id') or '')
    checkout_id = str(session.get('client_reference_id') or '')
    if not sid.startswith('cs_test_') or not checkout_id:
        raise HTTPException(400, 'Invalid Checkout session')
    # Never trust platform or data directory from the public event.
    for platform in ('doorks', 'sdc'):
        path = location(request, platform, 'estimates_invoices').parent / 'moses_stripe_checkout.json'
        with _locked(path):
            rows = load(path)
            row = next((r for r in rows if r['id'] == checkout_id and r.get('stripe_session_id') == sid), None)
            if row is None:
                continue
            snap = row['snapshot']
            if (session.get('currency') != 'usd' or session.get('amount_total') != snap['amount_cents']
                    or session.get('mode') != 'payment'
                    or session.get('metadata', {}).get('moses_checkout_id') != checkout_id):
                raise HTTPException(409, 'Stripe payment does not match saved invoice checkout')
            if row['state'] == 'paid':
                return {'received': True, 'processed': False, 'duplicate': True}
            if row['state'] != 'checkout_ready':
                raise HTTPException(409, 'Checkout was not confirmed as created')
            # Recheck source invoice before declaring that payment applies to it.
            invoices = load(location(request, platform, 'estimates_invoices'))
            current = next((i for i in invoices if i.get('id') == snap['record_id'] and i.get('document_type') == 'invoice'), None)
            if (current is None or str(current.get('document_number') or '') != snap['number']
                    or str(current.get('status') or '').strip().lower() not in ('sent', 'issued', 'open', 'unpaid')
                    or _money(current.get('total', current.get('amount'))) != snap['amount_cents']):
                row['state'] = 'reconciliation_required'
                save(path, rows)
                return {'received': True, 'processed': False, 'reconciliation_required': True}
            row.update(state='paid', paid_at=_now(), stripe_payment_intent=str(session.get('payment_intent') or ''), stripe_event_id=str(event.get('id') or ''))
            save(path, rows)
            # Do not mutate invoices/QuickBooks until their status and refund rules are integrated.
            return {'received': True, 'processed': True}
    raise HTTPException(404, 'Unknown Stripe Checkout session')


def history(request, platform, record_id):
    _admin(request, platform)
    return [_public(r) for r in load(_path(request, platform)) if r['snapshot']['record_id'] == record_id][-50:]


def payment_status(request, platform, record_id):
    """Read-only, invoice-bound Stripe verification. Never post to accounting here.

    A paid Stripe checkout is not proof that the invoice's own accounting ledger
    has been reconciled. Expose both facts separately to staff and Moses.
    """
    _admin(request, platform)
    invoice = _find_record(request, platform, 'invoice', record_id)
    saved = load(_path(request, platform))
    matches = [r for r in saved if r.get('snapshot', {}).get('record_id') == record_id]
    current_number = str(invoice.get('document_number') or '').strip()
    current_total = None
    try:
        current_total = _money(invoice.get('total', invoice.get('amount')))
    except HTTPException:
        pass
    result = []
    for row in matches[-20:]:
        snap = row['snapshot']
        matches_invoice = (snap['number'] == current_number
                           and snap['amount_cents'] == current_total)
        state = row['state']
        result.append({
            'checkout_id': row['id'], 'state': state,
            'amount_cents': snap['amount_cents'], 'currency': snap['currency'],
            'matches_current_invoice': matches_invoice,
            'stripe_payment_confirmed': state == 'paid',
            'paid_at': row.get('paid_at') if state == 'paid' else None,
        })
    confirmed = [r for r in result if r['stripe_payment_confirmed'] and r['matches_current_invoice']]
    mismatch = any(r['stripe_payment_confirmed'] and not r['matches_current_invoice'] for r in result)
    return {
        'platform': platform, 'record_id': record_id,
        'invoice_number': current_number, 'invoice_status': str(invoice.get('status') or ''),
        'stripe_payment_confirmed': bool(confirmed),
        'stripe_payment_requires_review': mismatch or any(r['state'] in ('uncertain', 'reconciliation_required') for r in result),
        'accounting_reconciled': False,  # No automated ledger posting exists yet.
        'checkouts': result,
        'note': ('Stripe payment verification is separate from invoice/accounting reconciliation. '
                 'Do not state that an invoice was fully reconciled or automatically marked Paid.'),
    }
