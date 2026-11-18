"""Offline HTTP smoke checks for cumulative PDS communication routes.

The real FastAPI app is exercised, but no providers are contacted and no
production filesystem or customer records are accessed by these requests.
"""
from fastapi.testclient import TestClient
from main import app


def test_public_a2p_pages_are_routable_without_a_login(monkeypatch):
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', 'https://dispatch.example.test')
    with TestClient(app) as client:
        for path, required in (
            ('/pds/sms', 'START'),
            ('/pds/sms/privacy', 'Privacy Policy'),
            ('/pds/sms/terms', 'STOP'),
        ):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
            assert required in response.text
            assert 'Priority Door Systems' in response.text


def test_unsigned_twilio_http_webhooks_are_denied(monkeypatch):
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', 'https://dispatch.example.test')
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'test-only-token')
    with TestClient(app) as client:
        inbound = client.post('/pds/sms/twilio/inbound', data={
            'From': '+17605550123', 'To': '+17606421131',
            'Body': 'START', 'MessageSid': 'SM' + 'a' * 32,
        })
        callback = client.post('/pds/sms/twilio/status', data={
            'MessageSid': 'SM' + 'a' * 32, 'MessageStatus': 'delivered',
        })
        assert inbound.status_code == 403
        assert callback.status_code == 403


def test_unauthenticated_write_endpoints_are_rejected():
    with TestClient(app) as client:
        email = client.post('/pds-schedule-notifications/email/proposals', json={
            'job_id': 'job1', 'recipient': 'customer@example.test',
            'category': 'appointment', 'subject': 'Appointment',
            'message': 'Priority Door Systems: Confirmed.',
        })
        van = client.post('/pds-van-stock/vans', json={'employee_id': 'test'})
        sms = client.post('/moses-action-center/pds/sms/proposals', json={
            'job_id': 'job1', 'phone': '+17605550123',
            'message': 'Priority Door Systems: Confirmation',
        })
        assert email.status_code in (401, 403)
        assert van.status_code in (401, 403, 422)
        assert sms.status_code in (401, 403)
