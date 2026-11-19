"""Public PDS SMS policy pages and signed Twilio keyword callback."""
from __future__ import annotations

import html
import os
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
# Verify Twilio form webhooks without requiring the optional Twilio SDK at import time.
import base64
import hashlib
import hmac


def _valid_twilio_signature(token, url, params, signature):
    # Twilio form webhook authentication: HMAC-SHA1 of exact public URL followed
    # by alphabetically sorted POST keys and their values. Reject absent signatures.
    if not signature or not token or not url.startswith('https://'):
        return False
    value = url + ''.join(str(k) + str(params[k]) for k in sorted(params))
    digest = hmac.new(token.encode(), value.encode(), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature.strip())
from app.services.pds_sms_consent import NUMBER, HELP_PHONE, handle_keyword

router = APIRouter(tags=['pds-sms'])
BRAND = 'Priority Door Systems'


def _urls(request, *, require_config=True):
    # Use an administrator-configured, publicly accessible HTTPS root; do not use Host header.
    root = os.getenv('PDS_SMS_PUBLIC_BASE_URL', '').rstrip('/')
    if not root.startswith('https://'):
        if require_config:
            raise HTTPException(503, 'PDS_SMS_PUBLIC_BASE_URL must be a public HTTPS URL')
        # Public policy pages must remain readable during configuration; inbound
        # signed webhooks still require an explicitly verified HTTPS base URL.
        root = ''
    return root, root + '/pds/sms/privacy', root + '/pds/sms/terms'


def _page(title, body):
    return HTMLResponse('''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>''' + html.escape(title) + ''' | Priority Door Systems</title>
<style>body{font:16px/1.6 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;background:#f6f8fa;color:#17212d}
main{max-width:720px;margin:48px auto;padding:36px;background:white;border:1px solid #e1e7ef;border-radius:16px}
header{font-weight:750;color:#113a66}h1{font-size:30px;line-height:1.2}a{color:#175aaa}small{color:#506174}
@media(max-width:650px){main{margin:0;padding:24px;border:0;border-radius:0}}</style></head><body><main>
<header>PRIORITY DOOR SYSTEMS</header><h1>''' + html.escape(title) + '</h1>' + body + '''
<hr><small>Priority Door Systems · <a href="/pds/sms">SMS Signup</a> ·
<a href="/pds/sms/privacy">Privacy Policy</a> · <a href="/pds/sms/terms">Terms &amp; Conditions</a></small>
</main></body></html>''', headers={'Cache-Control': 'public, max-age=300'})


@router.get('/pds/sms', response_class=HTMLResponse)
def signup(request: Request):
    root, privacy, terms = _urls(request, require_config=False)
    phone = html.escape(NUMBER)
    return _page('SMS Service Updates', f'''<p>To request SMS service updates from Priority Door Systems,
text <strong>START</strong> to <strong>{phone}</strong> from your mobile phone.</p>
<p>We will ask you to reply <strong>YES</strong> to confirm. You will not be enrolled until you confirm.</p>
<p>Messages include appointment confirmations, technician ETAs, and updates about your door service work.
Message frequency varies. Message and data rates may apply.</p>
<p>Reply <strong>STOP</strong> at any time to unsubscribe, or <strong>HELP</strong> for assistance.
For help you can also call {html.escape(HELP_PHONE)}.</p>
<p>Consent is voluntary and is not a condition of purchasing services.</p>
<p><a href="{html.escape(privacy,quote=True)}">Privacy Policy</a> ·
<a href="{html.escape(terms,quote=True)}">Terms &amp; Conditions</a></p>
<p><strong>Keyword exchange:</strong><br>Customer: START<br>Priority Door Systems: Please reply YES to confirm service messages.<br>
Customer: YES<br>Priority Door Systems: Subscription confirmed; STOP to cancel, HELP for help.</p>''')


@router.get('/pds/sms/privacy', response_class=HTMLResponse)
def privacy(request: Request):
    _urls(request, require_config=False)
    return _page('Privacy Policy', '''<p><strong>Effective November 18, 2026.</strong> Priority Door Systems collects
mobile telephone numbers and SMS consent records when customers request service notifications.
We use this data for appointment confirmations, technician ETAs, service updates, opt-out handling,
and customer support.</p><p>We do not sell or share SMS opt-in data or mobile phone numbers with
third parties or affiliates for marketing or promotional purposes. We may use service providers
solely to deliver requested operational messages, subject to appropriate safeguards.</p>
<p>Our systems may retain your opt-in/opt-out status and related communications to honor your
choices and maintain compliance. Access is limited to authorized personnel and service providers.
You may opt out any time by replying STOP; reply HELP for support.</p>
<p>Message frequency varies and message/data rates may apply. For privacy questions contact
<a href="mailto:reception@prioritydoors.com">reception@prioritydoors.com</a>.</p>''')


@router.get('/pds/sms/terms', response_class=HTMLResponse)
def terms(request: Request):
    _urls(request, require_config=False)
    return _page('Terms & Conditions', f'''<p><strong>Effective November 18, 2026.</strong> By texting START to
<strong>{html.escape(NUMBER)}</strong> and confirming with YES, you consent to receive service-related
texts from Priority Door Systems, including appointment confirmations, technician arrival estimates,
and job updates.</p><p>Message frequency varies. Message and data rates may apply.
Consent is optional and not a condition of purchasing any goods or services.</p>
<p>Reply <strong>STOP</strong> to unsubscribe at any time, or <strong>HELP</strong> for support.
You can also call {html.escape(HELP_PHONE)}. Carriers are not responsible for delayed or undelivered
messages. Refer to our <a href="/pds/sms/privacy">Privacy Policy</a>.</p>''')


@router.post('/pds/sms/twilio/inbound')
async def twilio_inbound(request: Request):
    token = os.getenv('TWILIO_AUTH_TOKEN', '')
    public, privacy_url, terms_url = _urls(request)
    if not token:
        raise HTTPException(503, 'SMS integration is not configured')
    form = await request.form()
    params = dict(form)
    expected_url = public + '/pds/sms/twilio/inbound'
    signature = request.headers.get('X-Twilio-Signature', '')
    if not _valid_twilio_signature(token, expected_url, params, signature):
        raise HTTPException(403, 'Invalid Twilio signature')
    incoming_to = params.get('To', '')
    if incoming_to.replace(' ', '') != NUMBER.replace(' ', ''):
        raise HTTPException(403, 'SMS destination mismatch')
    try:
        reply, _state = handle_keyword(request.app.state.data_dir, params.get('From', ''),
                            params.get('MessageSid', ''), params.get('Body', ''),
                            privacy_url=privacy_url, terms_url=terms_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response('<Response><Message>' + escape(reply) + '</Message></Response>',
                    media_type='application/xml')

@router.post('/pds/sms/twilio/status')
async def twilio_status(request:Request):
    """Signed Twilio delivery callback. Only a provider SID can update status."""
    token=os.getenv('TWILIO_AUTH_TOKEN','')
    public,_,_=_urls(request)
    if not token:
        raise HTTPException(503,'Twilio provider not configured')
    params=dict(await request.form())
    # The proposal ID is part of the signed public callback URL. Do not trust
    # client-supplied IDs outside Twilio's signed URL.
    proposal_id = request.query_params.get('proposal_id')
    url = public + '/pds/sms/twilio/status'
    if proposal_id is not None:
        url += '?proposal_id=' + proposal_id
    if not _valid_twilio_signature(token,url,params,
                                   request.headers.get('X-Twilio-Signature','')):
        raise HTTPException(403,'Invalid Twilio signature')
    from app.services.moses_pds_twilio import reconcile_status
    try:
        reconcile_status(request.app.state.data_dir,params.get('MessageSid',''),
                         params.get('MessageStatus',''),proposal_id)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    return Response('<Response/>',media_type='application/xml')
