"""Opt-in, approved purchase-order PDF delivery through existing SMTP settings.

No customer estimate/invoice sending here: secure customer portal / Stripe
are not yet verified. Never retry ambiguous SMTP delivery automatically.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from pathlib import Path
from threading import RLock
from xml.sax.saxutils import escape
from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from app.services.moses_delivery import preview, _find_record, _email

_LOCK = RLock()

def _now():
    return datetime.now(timezone.utc).isoformat()

def _guard(request, platform):
    if platform not in ('doorks', 'sdc', 'pds'):
        raise HTTPException(400, 'Unknown business platform')
    if not getattr(request.state, 'auth_user', None) or getattr(request.state, 'auth_role', None) != 'office_admin' or request.session.get('active_platform') != platform:
        raise HTTPException(403, 'Active workspace office administrator required')
    if os.getenv('MOSES_PO_SEND_ENABLED', '').lower().strip() != 'true':
        raise HTTPException(503, 'Purchase-order email sending is disabled')

def _path(request, platform):
    base = Path(request.app.state.data_dir)
    folder = base / ('moses_pds' if platform == 'pds' else 'business_workspaces/' + platform)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'moses_po_delivery_actions.json'

def _read(path):
    from app.routers.workspaces import load
    return load(path)

def _write(path, rows):
    from app.routers.workspaces import save
    save(path, rows)

def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else str(user)

def _supplier_email(request, platform, item):
    # Direct vendor email wins if recorded on the PO itself.
    for key in ('vendor_email', 'supplier_email', 'email', 'contact_email'):
        if item.get(key):
            address = _email(item[key])
            if not address:
                raise HTTPException(409, 'Invalid vendor email on purchase order')
            return address
    sid = str(item.get('supplier_id') or item.get('vendor_id') or '').strip()
    if not sid:
        return ''
    if platform == 'pds':
        from app.routers.pds_purchase_orders import _supplier_path, _read as read
        candidates = read(_supplier_path(request), [])
    else:
        from app.routers.workspaces import guard, location, load
        guard(request, platform, 'vendors')
        candidates = load(location(request, platform, 'vendors'))
    matches = [v for v in candidates if str(v.get('id')) == sid]
    if len(matches) != 1:
        raise HTTPException(409, 'Linked supplier could not be uniquely verified')
    raw = str(matches[0].get('email') or '').strip()
    if raw and not _email(raw):
        raise HTTPException(409, 'Linked supplier email is invalid')
    return _email(raw)

def _line_items(item):
    raw = item.get('line_items') or ''
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raise HTTPException(409, 'Purchase order line items cannot be read')
    if isinstance(raw, list):
        if len(raw) > 100:
            raise HTTPException(409, 'Too many line items for email PDF')
        rows = []
        for line in raw:
            if not isinstance(line, dict):
                raise HTTPException(409, 'Invalid purchase-order line item')
            desc = str(line.get('description') or line.get('item') or '').strip()
            qty = str(line.get('quantity') or line.get('qty') or '').strip()
            price = str(line.get('unit_cost') or line.get('rate') or line.get('unit_price') or '').strip()
            if not desc or not qty or not price:
                raise HTTPException(409, 'Purchase order line is missing a description, quantity, or price')
            rows.append((desc[:500], qty[:30], price[:30]))
        if rows:
            return rows
    desc = str(item.get('description') or item.get('item_type') or '').strip()
    qty = str(item.get('quantity') or '').strip()
    price = str(item.get('unit_cost') or '').strip()
    if not all((desc, qty, price)):
        raise HTTPException(409, 'PO must have reviewed line items before emailing')
    return [(desc[:500], qty[:30], price[:30])]

def _snapshot(request, platform, record_id):
    _guard(request, platform)
    item = _find_record(request, platform, 'purchase_order', record_id)
    data = preview(request, platform, 'purchase_order', record_id)
    number = data.get('document_number', '')
    if not re.fullmatch(r'PO-[0-9]{1,10}', number):
        raise HTTPException(409, 'Verified official PO number is required')
    recipient = _supplier_email(request, platform, item) or data.get('to', '')
    if not recipient:
        raise HTTPException(409, 'Verified vendor email is required')
    if str(item.get('status') or '').lower() in ('cancelled', 'canceled', 'void'):
        raise HTTPException(409, 'Cancelled POs cannot be sent')
    if not all(data.get(k) for k in ('from', 'reply_to')):
        raise HTTPException(409, 'Company sender and purchasing Reply-To must be configured')
    rows = _line_items(item)
    total = str(item.get('total') if item.get('total') not in (None, '') else item.get('amount') or '').strip()
    if not total:
        raise HTTPException(409, 'PO total is missing; review amounts before email')
    try:
        amount = Decimal(total)
        if not amount.is_finite() or amount < 0:
            raise ValueError()
        for _, qty, price in rows:
            if Decimal(qty) <= 0 or Decimal(price) < 0:
                raise ValueError()
        subtotal = sum(Decimal(qty) * Decimal(price) for _, qty, price in rows)
        tax = Decimal(str(item.get('tax') or 0))
        shipping = Decimal(str(item.get('shipping') or 0))
        if tax < 0 or shipping < 0 or abs((subtotal + tax + shipping) - amount) > Decimal('0.02'):
            raise ValueError()
    except (ValueError, InvalidOperation):
        raise HTTPException(409, 'PO total does not match reviewed line items, tax, and shipping')
    vendor = str(item.get('vendor') or item.get('supplier') or '').strip()
    if not vendor:
        raise HTTPException(409, 'Vendor name is required')
    from app.services.moses_mail_identity import identity, general_inquiry_footer
    pds_footer = general_inquiry_footer(platform, identity(platform, 'purchase_order'))
    return {'platform':platform, 'record_id':record_id, 'number':number, 'vendor':vendor[:200],
            'business_name':{'pds':'Priority Door Systems','doorks':'Doorks','sdc':'Saddleback Design Co.'}[platform],
            'to':recipient, 'from':data['from'], 'reply_to':data['reply_to'], 'cc':data.get('cc') or '',
            'subject':data['subject'], 'text': 'Please find attached purchase order '+number+'.\n\nPlease reply if you have questions.' + pds_footer,
            'date':str(item.get('date') or '')[:30], 'ship_to':str(item.get('ship_to') or '')[:300],
            'notes':str(item.get('notes') or '')[:1000], 'lines':rows, 'total':total}

def _fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()

def _public(row):
    msg=row['snapshot']
    return {'id':row['id'], 'platform':row['platform'], 'record_id':row['record_id'],
            'state':row['state'], 'to':msg['to'], 'subject':msg['subject'],
            'reply_to':msg['reply_to'], 'cc':msg['cc'], 'number':msg['number'],
            'total':msg['total'], 'line_count':len(msg['lines']),
            'attachment_filename':msg['number']+'.pdf', 'requested_at':row['requested_at'],
            'transport':row.get('transport'),'delivery_status':row.get('delivery_status'),
            'provider_message_id':row.get('provider_message_id')}

def propose(request, platform, record_id):
    snap = _snapshot(request, platform, record_id)
    fp = _fingerprint(snap)
    with _LOCK:
        path = _path(request, platform)
        rows = _read(path)
        if any(r.get('record_id') == record_id and r.get('state') in ('sending', 'uncertain') for r in rows):
            raise HTTPException(409, 'A previous PO delivery is unconfirmed; reconcile it before preparing another send')
        existing = next((r for r in rows if r.get('fingerprint') == fp and r.get('state') in ('pending','sending','sent','uncertain')), None)
        if existing:
            if existing['state'] == 'pending':
                return {'proposal':_public(existing), 'approval_required':True, 'sent':False}
            raise HTTPException(409, 'Identical PO email already sent or may have been sent; review history')
        row={'id':uuid.uuid4().hex, 'platform':platform, 'record_id':record_id,
             'fingerprint':fp, 'snapshot':snap, 'state':'pending',
             'requested_at':_now(), 'requested_by':_actor(request)}
        rows.append(row)
        _write(path, rows)
        return {'proposal':_public(row), 'approval_required':True, 'sent':False}

def _pdf(snap):
    """Generate an attachment only from the reviewed, server-verified PO snapshot."""
    stream=io.BytesIO()
    doc=SimpleDocTemplate(stream, pagesize=letter, leftMargin=42,rightMargin=42, topMargin=40,bottomMargin=40)
    styles=getSampleStyleSheet()
    def para(s): return Paragraph(escape(str(s)).replace('\n','<br/>'),styles['Normal'])
    story=[Paragraph(escape(snap['business_name']),styles['Heading2']),
           Paragraph('PURCHASE ORDER '+escape(snap['number']),styles['Title']),Spacer(1,15),
           para('Vendor: '+snap['vendor']),para('Date: '+snap['date']),
           para('Ship To: '+snap['ship_to']),Spacer(1,12)]
    rows=[[para('Description'),para('Qty'),para('Unit Cost')]]+[[para(a),para(b),para(c)] for a,b,c in snap['lines']]
    table=Table(rows,colWidths=[350,65,105],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eef3')),
                               ('GRID',(0,0),(-1,-1),0.25,colors.grey),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([table,Spacer(1,14),para('PO Total: '+snap['total']),Spacer(1,14),para('Notes: '+snap['notes'])])
    doc.build(story)
    result=stream.getvalue()
    if not result.startswith(b'%PDF') or len(result)>2_000_000:
        raise HTTPException(500, 'Unable to prepare a verified PDF attachment')
    return result

def _transmit(snapshot, pdf_bytes):
    from app.services.moses_email_transport import provider, send_resend
    if provider() == 'resend':
        return send_resend(snapshot, pdf_bytes)
    host=os.getenv('DOORKS_SMTP_HOST','').strip()
    username=os.getenv('DOORKS_SMTP_USERNAME','').strip()
    password=os.getenv('DOORKS_SMTP_PASSWORD','')
    sender=os.getenv('DOORKS_SMTP_FROM','').strip()
    if not all((host,username,password,sender)) or sender.casefold()!=snapshot['from'].casefold():
        raise HTTPException(503, 'SMTP sender configuration is missing or mismatched')
    try: port=int(os.getenv('DOORKS_SMTP_PORT','465'))
    except ValueError: raise HTTPException(503,'Invalid SMTP port')
    if port < 1 or port > 65535: raise HTTPException(503,'Invalid SMTP port')
    mail=EmailMessage()
    for header,key in [('From','from'),('To','to'),('Reply-To','reply_to'),('Subject','subject')]:
        if '\r' in snapshot[key] or '\n' in snapshot[key]: raise HTTPException(422,'Invalid mail header')
        mail[header]=snapshot[key]
    if snapshot.get('cc'):
        if '\r' in snapshot['cc'] or '\n' in snapshot['cc']: raise HTTPException(422,'Invalid CC')
        mail['Cc']=snapshot['cc']
    mail.set_content(snapshot['text'])
    mail.add_attachment(pdf_bytes, maintype='application',subtype='pdf',filename=snapshot['number']+'.pdf')
    context=ssl.create_default_context()
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=15,context=context) as smtp:
            smtp.login(username,password);smtp.send_message(mail)
    else:
        with smtplib.SMTP(host,port,timeout=15) as smtp:
            smtp.starttls(context=context);smtp.login(username,password);smtp.send_message(mail)

def decide(request, platform, proposal_id, approve):
    _guard(request,platform)
    with _LOCK:
        path=_path(request,platform)
        rows=_read(path)
        row=next((r for r in rows if r.get('id')==proposal_id and r.get('platform')==platform),None)
        if row is None: raise HTTPException(404,'PO email proposal not found')
        if row['state']!='pending': raise HTTPException(409,'Proposal already processed')
        if not approve:
            row.update(state='rejected',decided_at=_now(),decided_by=_actor(request))
            _write(path,rows)
            return {'state':'rejected','sent':False,'proposal_id':proposal_id}
        try:
            snap=_snapshot(request,platform,row['record_id'])
        except HTTPException as exc:
            if exc.status_code in (404, 409):
                row.update(state='stale',decided_at=_now())
                _write(path,rows)
            raise
        if _fingerprint(snap)!=row['fingerprint']:
            row.update(state='stale',decided_at=_now());_write(path,rows)
            raise HTTPException(409,'PO details or recipient changed; prepare a new proposal')
        # Validate connection setup and create PDF before moving to 'sending'.
        from app.services.moses_email_transport import ready
        ready(snap['from'])
        pdf=_pdf(snap)
        row.update(state='sending',decided_by=_actor(request),decided_at=_now())
        _write(path,rows)
        try:
            receipt_id = _transmit(snap,pdf)
            from app.services.moses_email_transport import delivery_receipt
            receipt = delivery_receipt(receipt_id)
        except Exception:
            row.update(state='uncertain',completed_at=_now());_write(path,rows)
            return {'state':'uncertain','sent':False,'proposal_id':proposal_id,
                    'message':'SMTP acceptance not confirmed. Verify with provider before retrying.'}
        row.update(state='sent',completed_at=_now(),**receipt);_write(path,rows)
        return {'state':'sent','sent':True,'proposal_id':proposal_id,'recipient':snap['to']}

def history(request,platform,record_id):
    _guard(request,platform)
    return [_public(r) for r in _read(_path(request,platform)) if r.get('record_id')==record_id][-50:]
