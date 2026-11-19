"""Offline Twilio signature and public consent page checks."""
import base64
import hashlib
import hmac

from app.routers.pds_sms import _valid_twilio_signature, signup, privacy, terms


def test_twilio_signature_rejects_tampering_and_missing_signature():
    url = 'https://doorks.example/pds/sms/twilio/inbound'
    params = {'Body': 'START', 'From': '+17605550123', 'To': '+17606421131', 'MessageSid': 'SM123'}
    payload = url + ''.join(k + params[k] for k in sorted(params))
    signed = base64.b64encode(hmac.new(b'test-token', payload.encode(), hashlib.sha1).digest()).decode()
    assert _valid_twilio_signature('test-token', url, params, signed)
    assert not _valid_twilio_signature('bad-token', url, params, signed)
    assert not _valid_twilio_signature('test-token', url, {**params, 'Body': 'STOP'}, signed)
    assert not _valid_twilio_signature('test-token', url, params, '')
    assert not _valid_twilio_signature('test-token', url.replace('https:', 'http:'), params, signed)


def test_public_pages_readable_before_webhook_origin_is_configured(monkeypatch):
    from fastapi import HTTPException
    from app.routers.pds_sms import _urls
    import pytest
    monkeypatch.delenv('PDS_SMS_PUBLIC_BASE_URL', raising=False)
    # Customers can review policy while A2P registration is in progress.
    assert b'START' in signup(None).body
    assert b'SMS opt-in' in privacy(None).body
    assert b'STOP' in terms(None).body
    # The signed callback still refuses to run without an HTTPS public origin.
    with pytest.raises(HTTPException) as exc:
        _urls(None)
    assert exc.value.status_code == 503
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', 'https://doorks.example')
    assert _urls(None)[0] == 'https://doorks.example'
