"""PDS supplier-pricing queue, attachments and approval-gated Resend requests.

Requests and attachments live under existing durable PDS data storage. A supplier
reply is recorded by authorized staff; provider acceptance is not inbox delivery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256
import re
from uuid import uuid4
from contextlib import contextmanager
import fcntl
import json
import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix='/pds-supplier-quotes', tags=['pds-supplier-quotes'])
STATES = {'draft', 'awaiting_supplier', 'quote_received', 'ready_for_estimate', 'closed'}
# Bounded RFQ documents, not inventory images or public web files.
FILE_TYPES = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg',
              '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_FILES = 8
MAX_TOTAL_BYTES = 12 * 1024 * 1024


class QuoteDraft(BaseModel):
    supplier_id: str = Field(default='', max_length=100)
    supplier_name: str = Field(default='', max_length=200)
    supplier_email: str = Field(default='', max_length=254)
    job_number: str = Field(default='', max_length=100)
    description: str = Field(min_length=3, max_length=2500)
    quantity: int = Field(default=1, ge=1, le=100000)
    notes: str = Field(default='', max_length=2000)
    email_subject: str = Field(default='', max_length=180)
    email_message: str = Field(default='', max_length=2000)


class QuoteUpdate(BaseModel):
    status: str
    supplier_quote_number: str = Field(default='', max_length=160)
    supplier_cost: float | None = Field(default=None, ge=0, le=100000000)
    lead_time: str = Field(default='', max_length=200)
    note: str = Field(default='', max_length=1000)


def _auth(request: Request, *, write: bool = False):
    user = getattr(request.state, 'auth_user', None)
    role = str(getattr(request.state, 'auth_role', '') or '')
    if not isinstance(user, dict) or role not in ('tech', 'lead', 'office', 'office_admin'):
        raise HTTPException(401, 'Sign in to PDS')
    if request.session.get('active_platform', 'pds') != 'pds':
        raise HTTPException(403, 'Switch to PDS workspace')
    if write and role not in ('lead', 'office', 'office_admin'):
        raise HTTPException(403, 'Office or lead permission required for supplier quotes')
    return {'id': str(user.get('id') or user.get('username') or '')[:120],
            'name': str(user.get('name') or user.get('username') or 'Staff')[:120],
            'role': role}


def _folder(request):
    root = Path(str(getattr(request.app.state, 'data_dir', '') or ''))
    if not str(getattr(request.app.state, 'data_dir', '') or ''):
        raise HTTPException(503, 'Durable data storage not configured')
    return root / 'pds_supplier_quotes'


@contextmanager
def _locked(request):
    folder = _folder(request)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'lock').open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield folder / 'requests.json'
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read(path):
    if not path.exists():
        return []
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Supplier quote history cannot be read') from exc
    if not isinstance(result, list):
        raise HTTPException(503, 'Supplier quote history needs review')
    return result


def _save(path, items):
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _supplier(request, supplier_id, supplier_name, supplier_email):
    from app.routers.pds_purchase_orders import _read as read, _supplier_path
    saved = read(_supplier_path(request), [])
    if supplier_id:
        record = next((s for s in saved if str(s.get('id')) == supplier_id and not s.get('deactivated_at')), None)
        if not record:
            raise HTTPException(422, 'Select an active saved supplier')
        # Never let an arbitrary email override a saved supplier identity.
        return record.get('name', ''), record.get('email', '')
    name = supplier_name.strip()
    if not name:
        raise HTTPException(422, 'Supplier required')
    if supplier_email and ('@' not in supplier_email or '\r' in supplier_email or '\n' in supplier_email):
        raise HTTPException(422, 'Invalid supplier email')
    return name, supplier_email.strip()


@router.get('/config')
def supplier_quote_email_config(request: Request):
    _auth(request, write=True)
    # The configured reply address must match the actual Resend send endpoint.
    return {'reply_to': os.getenv('PDS_SUPPLIER_QUOTES_REPLY_TO', 'reception@prioritydoors.com').strip()}


@router.get('')
def list_quotes(request: Request, q: str = '', status: str = ''):
    _auth(request)
    with _locked(request) as path:
        rows = _read(path)
    query = q.casefold().strip()
    items = [r for r in rows if (not status or r.get('status') == status) and
             (not query or query in ' '.join(str(r.get(k) or '') for k in
             ('supplier_name', 'job_number', 'description', 'supplier_quote_number')).casefold())]
    return {'items': sorted(items, key=lambda x: x.get('updated_at', ''), reverse=True)[:500]}


@router.post('')
def create_quote(payload: QuoteDraft, request: Request):
    actor = _auth(request, write=True)
    name, email = _supplier(request, payload.supplier_id, payload.supplier_name, payload.supplier_email)
    now = _now()
    row = {'id': uuid4().hex, 'supplier_id': payload.supplier_id,
           'supplier_name': name, 'supplier_email': email,
           'job_number': payload.job_number.strip(), 'description': payload.description.strip(),
           'quantity': payload.quantity, 'notes': payload.notes.strip(),
           'email_subject': payload.email_subject.strip(),
           'email_message': payload.email_message.strip(), 'attachments': [],
           'status': 'draft', 'supplier_quote_number': '', 'supplier_cost': None,
           'lead_time': '', 'created_at': now, 'updated_at': now,
           'created_by': actor['name'], 'created_by_id': actor['id'],
           'history': [{'status': 'draft', 'at': now, 'by': actor['name'],
                        'action': 'created', 'note': 'Request saved; no email sent'}]}
    with _locked(request) as path:
        rows = _read(path)
        rows.append(row)
        _save(path, rows)
    return {'item': row}


def _safe_subject(row):
    subject = (row.get('email_subject') or '').strip() or (
        'PDS Pricing Request' + (' — Job ' + row['job_number'] if row.get('job_number') else ''))
    if any(c in subject for c in '\r\n'):
        raise HTTPException(422, 'Invalid email subject')
    return subject[:180]


def _email_details(row, supplier_name):
    """One consistent, readable message used both for preview and actual send."""
    message = [f'Hello {supplier_name},', '',
               'Please provide a quote for the following:', '',
               f"{row['quantity']} × {row['description']}"]
    if row.get('job_number'):
        message.append('Job: ' + row['job_number'])
    if row.get('notes'):
        message.extend(['', 'Specifications / notes:', row['notes']])
    if row.get('email_message'):
        message.extend(['', row['email_message']])
    message.extend(['', 'Please include your quote number, unit cost, freight (if applicable),'
                    ' lead time and availability.', '',
                    'Please reply directly to this email.', '', 'Priority Door Systems'])
    return '\n'.join(message)


def _attachment_file(request, quote_id, attachment):
    """File name is generated server-side, never controlled by the uploader."""
    identifier = str(attachment.get('id') or '')
    ext = str(attachment.get('extension') or '')
    if not re.fullmatch('[a-f0-9]{32}', quote_id) or not re.fullmatch('[a-f0-9]{32}', identifier) or ext not in FILE_TYPES:
        raise HTTPException(503, 'Saved supplier attachment reference invalid')
    return _folder(request) / 'attachments' / quote_id / (identifier + ext)


def _find_quote(rows, quote_id):
    row = next((r for r in rows if r.get('id') == quote_id), None)
    if not row:
        raise HTTPException(404, 'Supplier quote request not found')
    return row


def _file_type(filename, content):
    name = str(filename or '')
    if not name or len(name) > 160 or '/' in name or '\\' in name or any(ord(ch) < 32 for ch in name):
        raise HTTPException(422, 'Invalid attachment name')
    ext = Path(name).suffix.lower()
    if ext not in FILE_TYPES:
        raise HTTPException(422, 'Attach PDF, PNG, JPEG or WebP files only')
    valid = {'.pdf': content.startswith(b'%PDF'),
             '.png': content.startswith(b'\x89PNG\r\n\x1a\n'),
             '.jpg': content.startswith(b'\xff\xd8\xff'),
             '.jpeg': content.startswith(b'\xff\xd8\xff'),
             '.webp': content.startswith(b'RIFF') and content[8:12] == b'WEBP'}
    if not valid[ext]:
        raise HTTPException(422, 'File content does not match its extension')
    return ext, FILE_TYPES[ext]


@router.put('/{quote_id}/draft')
def edit_quote_draft(quote_id: str, payload: QuoteDraft, request: Request):
    actor = _auth(request, write=True)
    name, email = _supplier(request, payload.supplier_id, payload.supplier_name, payload.supplier_email)
    with _locked(request) as path:
        rows = _read(path)
        row = _find_quote(rows, quote_id)
        if row.get('status') != 'draft':
            raise HTTPException(409, 'Only unsent drafts may be edited')
        row.update(supplier_id=payload.supplier_id, supplier_name=name, supplier_email=email,
                   job_number=payload.job_number.strip(), description=payload.description.strip(),
                   quantity=payload.quantity, notes=payload.notes.strip(),
                   email_subject=payload.email_subject.strip(), email_message=payload.email_message.strip(),
                   updated_at=_now(), updated_by=actor['name'])
        row.setdefault('history', []).append({'action': 'draft_edited', 'status': 'draft',
                                             'at': row['updated_at'], 'by': actor['name']})
        _save(path, rows)
    return {'item': row}


@router.post('/{quote_id}/attachments')
async def upload_quote_attachment(quote_id: str, request: Request,
                                  file: UploadFile = File(...), purpose: str = Form('request')):
    actor = _auth(request, write=True)
    if purpose not in ('request', 'response'):
        raise HTTPException(422, 'Invalid attachment purpose')
    try:
        content = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    if not content or len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, 'Each attachment must be 4 MB or smaller')
    extension, mime = _file_type(file.filename, content)
    with _locked(request) as path:
        rows = _read(path)
        row = _find_quote(rows, quote_id)
        status = row.get('status')
        if purpose == 'request' and status != 'draft':
            raise HTTPException(409, 'Request attachments can only be added before sending')
        if purpose == 'response' and status not in ('awaiting_supplier', 'quote_received', 'ready_for_estimate'):
            raise HTTPException(409, 'Record a supplier response after the request has been sent')
        existing = row.setdefault('attachments', [])
        if len(existing) >= MAX_FILES or sum(int(a.get('size') or 0) for a in existing) + len(content) > MAX_TOTAL_BYTES:
            raise HTTPException(413, 'Supplier request attachment limit reached')
        digest = sha256(content).hexdigest()
        if any(a.get('sha256') == digest and a.get('purpose') == purpose for a in existing):
            raise HTTPException(409, 'This file is already attached')
        entry = {'id': uuid4().hex, 'filename': file.filename, 'extension': extension,
                 'mime': mime, 'size': len(content), 'sha256': digest,
                 'purpose': purpose, 'uploaded_at': _now(), 'uploaded_by': actor['name']}
        location = _attachment_file(request, quote_id, entry)
        location.parent.mkdir(parents=True, exist_ok=True)
        try:
            with location.open('xb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            existing.append(entry)
            row['updated_at'] = entry['uploaded_at']
            row.setdefault('history', []).append({'action': 'attachment_added',
                  'status': status, 'at': entry['uploaded_at'], 'by': actor['name'],
                  'note': purpose + ': ' + file.filename})
            _save(path, rows)
        except Exception:
            location.unlink(missing_ok=True)
            raise
    return {'attachment': entry, 'item': row}


@router.get('/{quote_id}/attachments/{attachment_id}')
def get_quote_attachment(quote_id: str, attachment_id: str, request: Request):
    _auth(request, write=True)
    with _locked(request) as path:
        row = _find_quote(_read(path), quote_id)
        attachment = next((a for a in row.get('attachments', []) if a.get('id') == attachment_id), None)
    if not attachment:
        raise HTTPException(404, 'Attachment not found')
    location = _attachment_file(request, quote_id, attachment)
    if not location.is_file():
        raise HTTPException(503, 'Attachment unavailable on durable storage')
    return FileResponse(location, media_type=attachment['mime'], filename=attachment['filename'],
                        content_disposition_type='inline',
                        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


def _verified_send_files(request, row):
    result = []
    for item in row.get('attachments', []):
        if item.get('purpose', 'request') != 'request':
            continue
        location = _attachment_file(request, row['id'], item)
        if not location.is_file():
            raise HTTPException(503, 'Missing supplier request attachment; no email sent')
        content = location.read_bytes()
        if len(content) != item['size'] or sha256(content).hexdigest() != item['sha256']:
            raise HTTPException(503, 'Supplier attachment changed; no email sent')
        _file_type(item['filename'], content)
        result.append({'filename': item['filename'], 'mime': item['mime'], 'content': content})
    return result


@router.get('/{quote_id}/email-preview')
def preview_supplier_email(quote_id: str, request: Request):
    _auth(request, write=True)
    from app.services.moses_delivery import _email
    with _locked(request) as path:
        row = _find_quote(_read(path), quote_id)
    name, address = _supplier(request, row.get('supplier_id') or '',
                              row.get('supplier_name') or '', row.get('supplier_email') or '')
    reply = os.getenv('PDS_SUPPLIER_QUOTES_REPLY_TO', 'reception@prioritydoors.com').strip()
    return {'status': row.get('status'), 'from': os.getenv('MOSES_DOCUMENTS_FROM', '').strip(),
            'to': address, 'recipient_verified': bool(_email(address)), 'reply_to': reply,
            'subject': _safe_subject(row), 'text': _email_details(row, name),
            'attachments': row.get('attachments', []), 'quote_id': quote_id}


class SendDecision(BaseModel):
    approve: bool


@router.post('/{quote_id}/send')
def send_supplier_request(quote_id: str, decision: SendDecision, request: Request):
    """Explicit authorized Resend approval with a durable uncertain-send hold.

    Provider acknowledgement does not prove inbox delivery. No automatic retry.
    """
    actor = _auth(request, write=True)
    if not decision.approve:
        raise HTTPException(422, 'Explicit send approval is required')
    from app.services.moses_delivery import _email
    from app.services.moses_email_transport import ready, send_resend
    sender = os.getenv('MOSES_DOCUMENTS_FROM', '').strip()
    reply = os.getenv('PDS_SUPPLIER_QUOTES_REPLY_TO', 'reception@prioritydoors.com').strip()
    ready(sender)
    if not _email(reply):
        raise HTTPException(503, 'Supplier quote reply-to address is invalid')
    with _locked(request) as path:
        rows = _read(path)
        row = _find_quote(rows, quote_id)
        if row.get('status') != 'draft':
            raise HTTPException(409, 'Request already processed; review history before sending another email')
        # Re-check the supplier directory at send time. Do not accept a new
        # recipient from the browser or from a generated text prompt.
        name, recipient = _supplier(request, row.get('supplier_id') or '',
                                     row.get('supplier_name') or '', row.get('supplier_email') or '')
        if not _email(recipient):
            raise HTTPException(422, 'Saved supplier email is required before sending')
        attachments = _verified_send_files(request, row)
        subject = _safe_subject(row)
        message_text = _email_details(row, name)
        now = _now()
        row['status'] = 'send_uncertain'
        row['send_intent_id'] = uuid4().hex
        row['send_requested_at'] = now
        row['updated_at'] = now
        row['updated_by'] = actor['name']
        row['supplier_email'] = recipient
        row.setdefault('history', []).append({'status': 'send_uncertain', 'at': now,
            'by': actor['name'], 'action': 'send_intent',
            'note': 'Email approval saved; awaiting Resend response'})
        intent = row['send_intent_id']
        _save(path, rows)
    message = {'from': sender, 'to': recipient, 'reply_to': reply,
               'subject': subject, 'text': message_text}
    if attachments:
        message['attachments'] = attachments
    try:
        provider_id = send_resend(message)
    except Exception:
        # The remote outcome may be ambiguous. Leave the saved intent and
        # block retry instead of potentially emailing the supplier twice.
        return {'state': 'uncertain', 'sent': False,
                'message': 'Provider outcome uncertain. Check Resend before any retry.'}
    with _locked(request) as path:
        rows = _read(path)
        latest = next((r for r in rows if r.get('id') == quote_id), None)
        if not latest or latest.get('send_intent_id') != intent:
            raise HTTPException(503, 'Saved send receipt needs review')
        now = _now()
        latest.update(status='awaiting_supplier', sent_via='resend',
                      delivery_status='accepted_by_provider',
                      provider_message_id=provider_id, sent_at=now, updated_at=now)
        latest.setdefault('history', []).append({'status': 'awaiting_supplier', 'at': now,
            'by': actor['name'], 'action': 'provider_accepted',
            'note': 'Resend accepted; inbox delivery unverified'})
        _save(path, rows)
    return {'state': 'accepted_by_provider', 'sent': True,
            'provider_message_id': provider_id, 'item': latest}


@router.patch('/{quote_id}')
def update_quote(quote_id: str, payload: QuoteUpdate, request: Request):
    actor = _auth(request, write=True)
    if payload.status not in STATES:
        raise HTTPException(422, 'Invalid quote status')
    if payload.status == 'awaiting_supplier' and not payload.note.strip():
        raise HTTPException(422, 'Record how the request was sent before marking awaiting supplier')
    if payload.status in ('quote_received', 'ready_for_estimate') and not payload.supplier_quote_number.strip():
        raise HTTPException(422, 'Supplier quote number required for received pricing')
    with _locked(request) as path:
        rows = _read(path)
        row = next((r for r in rows if r.get('id') == quote_id), None)
        if not row:
            raise HTTPException(404, 'Supplier quote request not found')
        if row.get('status') == 'send_uncertain':
            raise HTTPException(409, 'Email send outcome uncertain; inspect Resend before changing the request')
        if row.get('status') == 'closed':
            raise HTTPException(409, 'Closed request is read-only; create a new request')
        if payload.status == 'ready_for_estimate' and payload.supplier_cost is None:
            raise HTTPException(422, 'Confirm supplier cost before marking ready')
        old = row.get('status')
        now = _now()
        row.update(status=payload.status, updated_at=now,
                   updated_by=actor['name'], supplier_quote_number=payload.supplier_quote_number.strip(),
                   supplier_cost=payload.supplier_cost, lead_time=payload.lead_time.strip())
        row.setdefault('history', []).append({'status': payload.status, 'previous_status': old,
                                              'at': now, 'by': actor['name'],
                                              'action': 'updated', 'note': payload.note.strip()})
        _save(path, rows)
    return {'item': row}
