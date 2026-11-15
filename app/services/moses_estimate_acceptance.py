"""Secure, customer-facing Doorks/SDC estimate acceptance.

Never sends mail or invokes payments. A link is a bearer capability, not
verified proof of a customer's identity. PDS remains on its existing workflow.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import uuid

from fastapi import HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from xml.sax.saxutils import escape

from app.routers.workspaces import guard, location, load, save

MAX_DAYS = 14


def _now():
    return datetime.now(timezone.utc)


def _stamp():
    return _now().isoformat()


def _path(request, platform):
    # Private, workspace-scoped metadata; never keep raw tokens on disk.
    return location(request, platform, 'estimates_invoices').parent / 'estimate_acceptance_links.json'


@contextmanager
def _locked(path: Path):
    # Use filesystem locking in addition to the server's in-process locks.
    # Both the link issuance and customer acceptance routes use this lock.
    lock_file = path.with_suffix('.lock')
    with open(lock_file, 'a+b') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _document(request, platform, record_id):
    rows = load(location(request, platform, 'estimates_invoices'))
    matches = [r for r in rows if str(r.get('id')) == record_id and
               str(r.get('document_type') or '').casefold() == 'estimate']
    if len(matches) != 1:
        raise HTTPException(404, 'Estimate not found')
    return rows, matches[0]


def _eligible(record):
    if str(record.get('status') or '').casefold() != 'sent':
        raise HTTPException(409, 'Estimate must have been issued and marked Sent')
    number = str(record.get('document_number') or '').strip()
    if not number or len(number) > 80:
        raise HTTPException(409, 'Estimate must have an official document number')
    if record.get('pricing_required') or record.get('requires_number_assignment'):
        raise HTTPException(409, 'Estimate pricing/numbering review is incomplete')
    try:
        amount = Decimal(str(record.get('total') or record.get('amount') or ''))
        if not amount.is_finite() or amount <= 0:
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise HTTPException(409, 'Estimate must have a reviewed positive total')
    # A customer cannot accept what the portal cannot faithfully render.
    _pdf_lines(record)
    return number, str(amount)


def _fingerprint(record):
    # A stale link must not approve a document altered after link generation.
    # Exclude irrelevant system metadata and use all client-controlled fields.
    relevant = {k: v for k,v in record.items() if k not in
                ('updated_at', 'approved_at', 'approved_by', 'accepted_at',
                 'accepted_by', 'acceptance_link_id')}
    return hashlib.sha256(json.dumps(relevant, sort_keys=True, default=str).encode()).hexdigest()


def _actor(request):
    u=request.state.auth_user
    return str(u.get('id') or u.get('username') or 'office_admin') if isinstance(u,dict) else str(u)


def issue(request, platform, record_id, *, days=7):
    """Admin issues one acceptance link; never changes the estimate or sends it."""
    if platform not in ('doorks','sdc'):
        raise HTTPException(404, 'Unsupported workspace')
    guard(request, platform, 'estimates_invoices')
    if not isinstance(days,int) or days < 1 or days > MAX_DAYS:
        raise HTTPException(400, 'Invalid link validity')
    path=_path(request,platform)
    with _locked(path):
        _,record=_document(request,platform,record_id)
        number, total=_eligible(record)
        links=load(path)
        if any(x.get('record_id') == record_id and x.get('state') == 'active' for x in links):
            raise HTTPException(409, 'An active link already exists; revoke it before creating another')
        token=secrets.token_urlsafe(32)
        row={'id':uuid.uuid4().hex, 'platform':platform, 'record_id':record_id,
             'token_hash':hashlib.sha256(token.encode()).hexdigest(),
             'document_fingerprint':_fingerprint(record),'document_number':number,
             'total':total,'state':'active', 'created_at':_stamp(),
             'expires_at':(_now()+timedelta(days=days)).isoformat(),
             'created_by':_actor(request)}
        links.append(row)
        save(path,links)
    # Only this response contains the raw bearer token. Never log or persist it.
    return {'token':token,'acceptance_path':'/doorks-assistant/public/estimates/accept#'+token,
            'link_id':row['id'], 'expires_at':row['expires_at'],
            'document_number':number,'sent':False,'email_sent':False,
            'warning':'Anyone holding the link can accept; verify recipients before sharing.'}


def revoke(request,platform,link_id):
    guard(request,platform,'estimates_invoices')
    path=_path(request,platform)
    with _locked(path):
        links=load(path)
        matches=[r for r in links if r.get('id')==link_id]
        if len(matches)!=1:
            raise HTTPException(404,'Link not found')
        row=matches[0]
        if row['state']!='active':
            raise HTTPException(409,'Link cannot be revoked in current state')
        row.update(state='revoked',revoked_at=_stamp(),revoked_by=_actor(request))
        save(path,links)
    return {'state':'revoked','link_id':link_id}


def history(request, platform, record_id):
    guard(request,platform,'estimates_invoices')
    return [{'id':r['id'],'state':r['state'],'created_at':r['created_at'],
             'expires_at':r['expires_at'],'accepted_at':r.get('accepted_at')}
            for r in load(_path(request,platform)) if r.get('record_id') == record_id]


def _resolve(request,token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{30,100}',token):
        raise HTTPException(404,'Link unavailable')
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    # Search only the two explicit customer workspaces; never PDS.
    for platform in ('doorks','sdc'):
        path=_path(request,platform)
        links=load(path)
        match=next((r for r in links if secrets.compare_digest(r.get('token_hash',''),token_hash)),None)
        if match:
            return platform,path,match
    raise HTTPException(404,'Link unavailable')


def _check(request,platform,row):
    if row['state']!='active':
        raise HTTPException(410,'Link has been used or revoked')
    try:
        expiry=datetime.fromisoformat(row['expires_at'])
    except (ValueError,KeyError):
        raise HTTPException(410,'Link expired')
    if expiry < _now():
        raise HTTPException(410,'Link expired')
    _,record=_document(request,platform,row['record_id'])
    _eligible(record)
    if _fingerprint(record)!=row['document_fingerprint']:
        raise HTTPException(409,'Estimate changed after link creation; request a new link')
    return record


def inspect(request,token):
    platform,_,row=_resolve(request,token)
    record=_check(request,platform,row)
    # Minimal public disclosure to bearer; no contacts, attachments, or notes.
    return {'document_number':row['document_number'],'total':row['total'],
            'business':{'doorks':'Doorks','sdc':'Saddleback Design Co.'}[platform],
            'expires_at':row['expires_at'],'status':'Awaiting acceptance'}


def accept(request,token,signer_name):
    if not isinstance(signer_name,str) or not 2 <= len(signer_name.strip()) <= 120:
        raise HTTPException(400,'Enter your name to accept')
    platform,path,row=_resolve(request,token)
    with _locked(path):
        links=load(path)
        match=next((r for r in links if r['id']==row['id']),None)
        if not match:
            raise HTTPException(404,'Link unavailable')
        record=_check(request,platform,match)
        docs_path=location(request,platform,'estimates_invoices')
        docs=load(docs_path)
        current=next(x for x in docs if x['id']==record['id'])
        # Store the approval on the existing business document, not a duplicate copy.
        current.update(status='Approved',accepted_at=_stamp(),accepted_by=signer_name.strip(),
                       acceptance_link_id=match['id'],updated_at=_stamp())
        save(docs_path,docs)
        match.update(state='accepted',accepted_at=current['accepted_at'],
                     accepted_by=signer_name.strip())
        save(path,links)
        return {'accepted':True,'document_number':match['document_number'],
                'accepted_at':match['accepted_at']}


def _money(value):
    try:
        dec = Decimal(str(value))
        if not dec.is_finite(): raise ValueError()
        return dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (ValueError, InvalidOperation, TypeError):
        raise HTTPException(409, 'Estimate contains invalid financial values')


def _pdf_lines(record):
    """Use the office editor's actual item fields; reject incomplete/mismatched totals."""
    raw = record.get('line_items')
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except (ValueError, TypeError): raise HTTPException(409, 'Estimate line items need review')
    if not isinstance(raw, list) or not raw or len(raw) > 100:
        raise HTTPException(409, 'Estimate needs reviewed line items before PDF viewing')
    result = []
    for line in raw:
        if not isinstance(line, dict): raise HTTPException(409, 'Estimate line item needs review')
        desc = str(line.get('description') or line.get('item') or '').strip()
        if not desc or len(desc) > 2000: raise HTTPException(409, 'Estimate line description needs review')
        quantity = _money(line.get('quantity'))
        price = _money(line.get('rate'))
        if quantity <= 0 or price < 0: raise HTTPException(409, 'Estimate line pricing needs review')
        result.append((desc, quantity, price, line.get('taxable') is not False))
    subtotal = sum((qty * rate for _, qty, rate, _ in result), Decimal('0'))
    taxable = sum((qty * rate for _, qty, rate, yes in result if yes), Decimal('0'))
    rate = _money(record.get('tax_rate') or 0)
    if rate < 0 or rate > 100: raise HTTPException(409, 'Estimate tax rate needs review')
    tax = (taxable * rate / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    declared_tax = record.get('tax_amount')
    if declared_tax not in ('', None) and abs(_money(declared_tax) - tax) > Decimal('0.02'):
        raise HTTPException(409, 'Estimate tax needs review')
    total = _money(record.get('amount') if record.get('amount') not in ('', None) else record.get('total'))
    if abs((subtotal + tax) - total) > Decimal('0.02'):
        raise HTTPException(409, 'Estimate total does not match line items and tax')
    return result, subtotal, tax, total, rate


def document_pdf(request, token):
    """Render a restricted, current PDF from the exact accepted-version document.

    This does not publish stored attachments or internal customer/work-order data.
    Access is the same expiring bearer capability used for acceptance.
    """
    platform, _, row = _resolve(request, token)
    record = _check(request, platform, row)
    lines, subtotal, tax, total, rate = _pdf_lines(record)
    if not str(record.get('customer') or '').strip():
        raise HTTPException(409, 'Estimate customer needs review')
    styles = getSampleStyleSheet()
    stream = io.BytesIO()
    pdf = SimpleDocTemplate(stream, pagesize=letter, rightMargin=48, leftMargin=48,
                            topMargin=48, bottomMargin=48)
    para = lambda text, style='Normal': Paragraph(escape(str(text or ''))[:5000].replace('\n','<br/>'), styles[style])
    company = {'doorks': 'Doorks', 'sdc': 'Saddleback Design Co.'}[platform]
    story = [para(company, 'Heading1'), para('ESTIMATE ' + row['document_number'], 'Heading2'), Spacer(1, 14)]
    for title, field in [('Date', 'date'), ('Prepared for', 'customer'), ('Service address', 'address'),
                         ('Job #', 'work_order_number'), ('PO #', 'po_number'), ('Terms', 'terms')]:
        if record.get(field):
            story.append(Paragraph('<b>' + escape(title) + ':</b> ' + escape(str(record[field]))[:1000], styles['Normal']))
    story.append(Spacer(1, 18))
    grid = [[para('Description'), para('Qty'), para('Rate'), para('Amount')]]
    for desc, qty, price, _ in lines:
        grid.append([para(desc[:2000]), para(str(qty)), para(f'${price:,.2f}'), para(f'${qty*price:,.2f}')])
    table = Table(grid, colWidths=[285, 58, 80, 80], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0), colors.HexColor('#EAF0F6')),
       ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),
       ('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),0.4, colors.lightgrey)]))
    story += [table, Spacer(1,16), para(f'Subtotal: ${subtotal:,.2f}'),
              para(f'Sales tax ({rate}%): ${tax:,.2f}'),
              para(f'TOTAL: ${total:,.2f}', 'Heading2')]
    if record.get('notes'): story.extend([Spacer(1,12), para('Notes / Scope', 'Heading3'), para(str(record['notes'])[:3000])])
    story.extend([Spacer(1,14), para('Please review this entire estimate before accepting the proposal.')])
    pdf.build(story)
    return stream.getvalue()
