"""Central server-side outbound email transport. No send without calling workflow approval.

Select MOSES_EMAIL_PROVIDER=resend for API delivery; default stays SMTP for
backward compatibility. No credentials, bearer links or attachments are logged.
"""
from __future__ import annotations
import base64
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from fastapi import HTTPException


def provider():
    name = os.getenv('MOSES_EMAIL_PROVIDER', '').strip().lower()
    if name != 'resend':
        raise HTTPException(503, 'Moses requires Resend; SMTP/Outlook disabled for Moses delivery')
    return name


def ready(sender):
    from app.services.moses_delivery import _email
    if not _email(sender):
        raise HTTPException(422, 'A valid sender address is required')
    if provider() == 'resend':
        if not os.getenv('RESEND_API_KEY', '').startswith('re_'):
            raise HTTPException(503, 'Resend API key not configured')
        configured = os.getenv('MOSES_DOCUMENTS_FROM', '').strip()
        if _email(configured) != _email(sender):
            raise HTTPException(503, 'Resend sender must match configured company sender')
        return
    needed = ('DOORKS_SMTP_HOST','DOORKS_SMTP_USERNAME','DOORKS_SMTP_PASSWORD','DOORKS_SMTP_FROM')
    if not all(os.getenv(x) for x in needed):
        raise HTTPException(503, 'SMTP is not configured')
    if _email(os.getenv('DOORKS_SMTP_FROM')) != _email(sender):
        raise HTTPException(503, 'SMTP sender does not match company sender')


def send_resend(message, pdf_bytes=None):
    """Raises on any unconfirmed API response; caller retains ambiguous-send hold."""
    ready(message['from'])
    def header(value):
        if not isinstance(value, str) or '\r' in value or '\n' in value:
            raise HTTPException(422, 'Invalid email header')
        return value.strip()
    payload = {'from':header(message['from']), 'to':[header(message['to'])],
               'subject':header(message['subject']), 'text':message['text'],
               'reply_to':header(message['reply_to'])}
    if message.get('cc'):
        payload['cc'] = [header(message['cc'])]
    if pdf_bytes is not None:
        if not pdf_bytes.startswith(b'%PDF') or len(pdf_bytes)>2_000_000:
            raise HTTPException(422, 'Invalid PDF attachment')
        number = header(message['number'])
        if '/' in number or '\\' in number:
            raise HTTPException(422, 'Invalid document number')
        payload['attachments'] = [{'filename':number+'.pdf',
                                  'content':base64.b64encode(pdf_bytes).decode('ascii')}]
    if message.get('attachments'):
        if pdf_bytes is not None:
            raise HTTPException(422, 'Choose one attachment source')
        from pathlib import Path
        types = {'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg',
                 '.jpeg':'image/jpeg','.webp':'image/webp'}
        files = message['attachments']
        if not isinstance(files, list) or len(files) > 8:
            raise HTTPException(422, 'Too many attachments')
        total = 0
        payload['attachments'] = []
        for item in files:
            name = header(item.get('filename', ''))
            raw = item.get('content')
            ext = Path(name).suffix.lower()
            if (not name or len(name) > 160 or '/' in name or '\\' in name or
                ext not in types or item.get('mime') != types.get(ext) or
                not isinstance(raw, bytes) or not raw):
                raise HTTPException(422, 'Invalid RFQ attachment')
            signatures = {'.pdf': raw.startswith(b'%PDF'),
                          '.png': raw.startswith(b'\x89PNG\r\n\x1a\n'),
                          '.jpg': raw.startswith(b'\xff\xd8\xff'),
                          '.jpeg': raw.startswith(b'\xff\xd8\xff'),
                          '.webp': raw.startswith(b'RIFF') and raw[8:12] == b'WEBP'}
            if not signatures[ext] or len(raw) > 4 * 1024 * 1024:
                raise HTTPException(422, 'RFQ attachment content invalid')
            total += len(raw)
            if total > 12 * 1024 * 1024:
                raise HTTPException(422, 'RFQ attachment total exceeds limit')
            payload['attachments'].append({'filename': name,
                                  'content': base64.b64encode(raw).decode('ascii')})
    body=json.dumps(payload).encode('utf-8')
    req=Request('https://api.resend.com/emails', data=body, method='POST',
                headers={'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],
                         'Content-Type':'application/json', 'User-Agent':'Doorks-Moses/1.0'})
    try:
        with urlopen(req, timeout=15) as resp:
            response=json.loads(resp.read(16384))
            if not (200<=resp.status<300 and response.get('id')):
                raise RuntimeError('Resend did not confirm acceptance')
            return response['id']
    except (HTTPError, URLError, ValueError, TimeoutError) as exc:
        raise RuntimeError('Resend delivery could not be confirmed; inspect provider logs') from exc


def delivery_receipt(result):
    """Provider acceptance, NOT proof of inbox delivery. No secret or URL stored."""
    if provider() == 'resend':
        if not isinstance(result, str) or not result or len(result)>256 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in result):
            raise RuntimeError('Resend did not return a valid delivery reference')
        return {'transport': 'resend', 'provider_message_id': result,
                'delivery_status': 'accepted_by_provider'}
    return {'transport': 'smtp', 'delivery_status': 'submitted_to_provider'}


def send_resend_attachment(message, attachment, filename, mime, *, idempotency_key):
    """Send a published original through Resend after approved portal validations.

    Returns provider acceptance ID, not inbox delivery. The caller passes a stable
    idempotency token based on the approved document/recipient/content.
    """
    import re
    from pathlib import Path
    from app.services.moses_delivery import _email
    ready(message['from'])
    if not isinstance(attachment, bytes) or not 1 <= len(attachment) <= 10*1024*1024:
        raise HTTPException(422,'Invalid document attachment size')
    mimetypes={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg',
               '.jpeg':'image/jpeg','.webp':'image/webp'}
    if (not isinstance(filename,str) or len(filename)>180 or
        filename!=Path(filename).name or any(c in filename for c in '\r\n\\/')):
        raise HTTPException(422,'Invalid document filename')
    extension=Path(filename).suffix.lower()
    if mimetypes.get(extension)!=mime:
        raise HTTPException(422,'Filename/attachment type mismatch')
    signatures={'.pdf':attachment.startswith(b'%PDF'),
                '.png':attachment.startswith(b'\x89PNG\r\n\x1a\n'),
                '.jpg':attachment.startswith(b'\xff\xd8'),
                '.jpeg':attachment.startswith(b'\xff\xd8'),
                '.webp':attachment.startswith(b'RIFF') and attachment[8:12]==b'WEBP'}
    if not signatures.get(extension):
        raise HTTPException(422,'Attachment content mismatch')
    if not isinstance(idempotency_key,str) or not re.fullmatch('[a-f0-9]{64}',idempotency_key):
        raise HTTPException(422,'Invalid idempotency key')
    def header(name):
        value=message.get(name)
        if not isinstance(value,str) or not value.strip() or '\r' in value or '\n' in value:
            raise HTTPException(422,'Invalid email header field')
        return value.strip()
    recipient=header('to');reply_to=header('reply_to')
    if not _email(recipient) or not _email(reply_to):
        raise HTTPException(422,'Invalid recipient/Reply-To')
    body={'from':header('from'),'to':[recipient],
          'subject':header('subject'),'text':header('text'),'reply_to':reply_to,
          'attachments':[{'filename':filename,'content':base64.b64encode(attachment).decode('ascii')}]}
    req=Request('https://api.resend.com/emails',data=json.dumps(body).encode('utf-8'),method='POST',headers={
        'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],
        'Content-Type':'application/json','User-Agent':'Doorks-Moses/2.0',
        'Idempotency-Key':idempotency_key})
    try:
        with urlopen(req,timeout=15) as response:
            data=json.loads(response.read(16384))
            if not (200 <= response.status < 300 and isinstance(data,dict) and data.get('id')):
                raise RuntimeError('Resend did not confirm acceptance')
            return data['id']
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise RuntimeError('Resend acceptance uncertain; check provider history') from exc
