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
    name = os.getenv('MOSES_EMAIL_PROVIDER', 'smtp').strip().lower()
    if name not in ('smtp', 'resend'):
        raise HTTPException(503, 'Unsupported outbound email provider')
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
