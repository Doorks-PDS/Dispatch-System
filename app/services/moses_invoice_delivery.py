"""Opt-in invoice PDF + saved Stripe TEST Checkout email; never posts accounting entries.

Only an approved request transmits. Ambiguous SMTP outcomes are held, not retried.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import fcntl
import hashlib
import json
import os
import uuid

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.routers.workspaces import load, save
from app.services import moses_stripe as stripe
from app.services import moses_estimate_acceptance as documents
from app.services.moses_delivery import _email, _find_record
from app.services.moses_po_delivery import _transmit


def _now():
    return datetime.now(timezone.utc).isoformat()


def _path(request, platform):
    return stripe._path(request, platform).parent / 'moses_invoice_delivery_actions.json'


@contextmanager
def _locked(path: Path):
    with open(path.with_suffix('.lock'), 'a+b') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'admin') if isinstance(user, dict) else str(user)


def _enabled(request, platform):
    stripe._admin(request, platform)
    if os.getenv('MOSES_INVOICE_SEND_ENABLED', '').lower() != 'true':
        raise HTTPException(503, 'Invoice email sending is disabled')
    stripe._enabled()  # explicit test-only key and flag


def _snapshot(request, platform, record_id):
    _enabled(request, platform)
    invoice = _find_record(request, platform, 'invoice', record_id)
    base = stripe._snapshot(request, platform, record_id)
    lines, subtotal, tax, total, tax_rate = documents._pdf_lines(invoice)
    if stripe._money(total) != base['amount_cents']:
        raise HTTPException(409, 'Invoice PDF total does not match Stripe amount')
    if not str(invoice.get('customer') or invoice.get('customer_name') or '').strip():
        raise HTTPException(409, 'Invoice customer name must be reviewed')
    sender = _email(os.getenv('MOSES_DOCUMENTS_FROM'))
    reply = _email(os.getenv('MOSES_INVOICES_REPLY_TO'))
    raw_cc = str(os.getenv('MOSES_INVOICES_CC') or '').strip()
    cc = _email(raw_cc) if raw_cc else ''
    if not sender or not reply or (raw_cc and not cc):
        raise HTTPException(409, 'Company invoice sender/Reply-To/CC is not configured')
    from app.services.moses_estimate_delivery import _smtp_ready
    _smtp_ready(sender)
    records = load(stripe._path(request, platform))
    candidates = [r for r in records if r.get('snapshot', {}).get('record_id') == record_id
                  and r.get('state') == 'checkout_ready']
    if len(candidates) != 1:
        raise HTTPException(409, 'Exactly one verified active Stripe Checkout is required')
    checkout = candidates[0]
    if checkout.get('fingerprint') != stripe._fingerprint(base):
        raise HTTPException(409, 'Invoice or AP recipient changed since Stripe Checkout')
    url = checkout.get('checkout_url') or ''
    from urllib.parse import urlsplit
    host = urlsplit(url)
    if host.scheme != 'https' or host.hostname not in ('checkout.stripe.com', 'checkout.stripe.dev') or host.username or host.password or host.fragment:
        raise HTTPException(409, 'Stored Stripe Checkout URL is invalid')
    if not str(checkout.get('stripe_session_id', '')).startswith('cs_test_'):
        raise HTTPException(409, 'Test Stripe session could not be verified')
    return {'platform': platform, 'record_id': record_id, 'number': base['number'],
            'to': base['recipient'], 'recipient_source': base['recipient_source'],
            'from': sender, 'reply_to': reply, 'cc': cc,
            'subject': 'Invoice ' + base['number'], 'checkout_id': checkout['id'],
            'stripe_session_id': checkout['stripe_session_id'],
            'amount_cents': base['amount_cents'], 'total': str(total),
            'document_hash': documents._fingerprint(invoice)}


def _fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def _public(row):
    s = row['snapshot']
    return {'id': row['id'], 'state': row['state'], 'platform': row['platform'],
            'record_id': row['record_id'], 'to': s['to'], 'recipient_source': s['recipient_source'],
            'from': s['from'], 'reply_to': s['reply_to'], 'cc': s['cc'],
            'subject': s['subject'], 'number': s['number'], 'total': s['total'],
            'attachment_filename': s['number'] + '.pdf',
            'checkout_id': s['checkout_id'], 'requested_at': row['requested_at'],
            'approval_required': row['state'] == 'pending', 'sent': row['state'] == 'sent',
            'transport': row.get('transport'), 'delivery_status': row.get('delivery_status'),
            'provider_message_id': row.get('provider_message_id')}


def propose(request, platform, record_id):
    snap = _snapshot(request, platform, record_id)
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        if any(r.get('record_id') == record_id and r.get('state') in ('sending', 'uncertain') for r in rows):
            raise HTTPException(409, 'Prior invoice delivery may have been sent; investigate before retry')
        fingerprint = _fingerprint(snap)
        previous = next((r for r in rows if r.get('fingerprint') == fingerprint and r['state'] in ('pending', 'sent')), None)
        if previous:
            if previous['state'] == 'sent':
                raise HTTPException(409, 'This invoice payment link was already emailed')
            return {'proposal': _public(previous)}
        row = {'id': uuid.uuid4().hex, 'platform': platform, 'record_id': record_id,
               'fingerprint': fingerprint, 'snapshot': snap, 'state': 'pending',
               'requested_at': _now(), 'requested_by': _actor(request)}
        rows.append(row)
        save(path, rows)
        return {'proposal': _public(row)}


def _invoice_pdf(record, snap):
    lines, subtotal, tax, total, tax_rate = documents._pdf_lines(record)
    if stripe._money(total) != snap['amount_cents']:
        raise HTTPException(409, 'Invoice PDF total changed')
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=letter, leftMargin=44, rightMargin=44)
    styles = getSampleStyleSheet()
    para = lambda value: Paragraph(escape(str(value))[:2000], styles['Normal'])
    company = 'Doorks' if snap['platform'] == 'doorks' else 'Saddleback Design Co.'
    contents = [Paragraph(escape(company), styles['Heading2']),
                Paragraph('INVOICE ' + escape(snap['number']), styles['Heading1']),
                Spacer(1, 12), para('Customer: ' + str(record.get('customer') or record.get('customer_name'))),
                Spacer(1, 12)]
    rows = [[para('Description'), para('Qty'), para('Rate'), para('Amount')]]
    for desc, qty, rate, _ in lines:
        rows.append([para(desc), para(qty), para('$' + str(rate)), para('$' + str(qty * rate))])
    table = Table(rows, colWidths=[270, 62, 82, 82], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EAF0F6')),
                               ('VALIGN', (0,0), (-1,-1), 'TOP'),
                               ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    contents.extend([table, Spacer(1, 15), para('Subtotal: $' + str(subtotal)),
                     para('Tax: $' + str(tax)), Paragraph('Total: $' + str(total), styles['Heading2'])])
    if record.get('terms'):
        contents.extend([Spacer(1, 12), para('Terms: ' + str(record['terms']))])
    doc.build(contents)
    result = stream.getvalue()
    if not result.startswith(b'%PDF') or len(result) > 2_000_000:
        raise HTTPException(500, 'Could not render invoice PDF')
    return result


def decide(request, platform, proposal_id, approve):
    _enabled(request, platform)
    path = _path(request, platform)
    with _locked(path):
        rows = load(path)
        row = next((r for r in rows if r['id'] == proposal_id and r['platform'] == platform), None)
        if not row:
            raise HTTPException(404, 'Invoice email proposal not found')
        if row['state'] != 'pending':
            raise HTTPException(409, 'Invoice email request was already processed')
        if not approve:
            row.update(state='rejected', decided_at=_now(), decided_by=_actor(request))
            save(path, rows)
            return {'state': 'rejected', 'sent': False}
        try:
            fresh = _snapshot(request, platform, row['record_id'])
            if _fingerprint(fresh) != row['fingerprint']:
                raise HTTPException(409, 'Invoice, recipient, or payment link changed')
            invoice = _find_record(request, platform, 'invoice', row['record_id'])
            pdf = _invoice_pdf(invoice, fresh)
        except HTTPException as exc:
            if exc.status_code in (404, 409):
                row.update(state='stale', decided_at=_now()); save(path, rows)
            raise
        row.update(state='sending', decided_at=_now(), decided_by=_actor(request))
        save(path, rows)
        # Link is fetched from the verified Stripe ledger only at execution time;
        # never persist the bearer URL in invoice-delivery audit records.
        sessions = load(stripe._path(request, platform))
        matching = [s for s in sessions if s.get('id') == fresh['checkout_id']
                    and s.get('state') == 'checkout_ready'
                    and s.get('stripe_session_id') == fresh['stripe_session_id']]
        if len(matching) != 1:
            row.update(state='uncertain', completed_at=_now()); save(path, rows)
            return {'state':'uncertain', 'sent': False, 'message':'Stripe link changed during delivery; inspect before retry'}
        message = dict(fresh)
        message['text'] = ('Please find your invoice ' + fresh['number'] + ' attached.\n\n'
                           'Pay securely using this Stripe TEST checkout link:\n' + matching[0]['checkout_url'] +
                           '\n\nPlease reply to this email with any questions.')
        try:
            receipt_id = _transmit(message, pdf)
            from app.services.moses_email_transport import delivery_receipt
            receipt = delivery_receipt(receipt_id)
        except Exception:
            row.update(state='uncertain', completed_at=_now()); save(path, rows)
            return {'state': 'uncertain', 'sent': False,
                    'message': 'SMTP delivery unconfirmed; review before sending again'}
        row.update(state='sent', completed_at=_now(), **receipt)
        save(path, rows)
        return {'state': 'sent', 'sent': True, 'number': fresh['number'], 'to': fresh['to']}


def history(request, platform, record_id):
    _enabled(request, platform)
    return [_public(r) for r in load(_path(request, platform)) if r.get('record_id') == record_id][-50:]
