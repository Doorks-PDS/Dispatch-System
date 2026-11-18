"""Offline HTTP acceptance: real routes, temporary durable storage, fake provider responses.

No live customer records, Twilio, Resend, or Render requests are made.
This does not establish A2P approval or live provider delivery.
"""
import base64
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.routers.pds_sms import router as public_sms
from app.routers.moses_pds_sms import router as customer_sms
from app.routers.pds_schedule_notifications import router as schedule_email
from app.services.pds_sms_consent import NUMBER, current_state


class Jobs:
    def get_job(self, job_id):
        return ({'id': 'ticket-123', 'phone': '+17605550111',
                 'email': 'guest@example.test'} if job_id == 'ticket-123' else None)


def _client(tmp_path):
    app = FastAPI()
    app.state.data_dir = str(tmp_path)
    app.state.calendar_store = Jobs()

    @app.middleware('http')
    async def signed_in_office(request: Request, call_next):
        request.state.auth_user = {'id': 'reviewer'}
        request.state.auth_role = 'office_admin'
        request.session['active_platform'] = 'pds'
        return await call_next(request)

    app.add_middleware(SessionMiddleware, secret_key='local-test-only')
    app.include_router(public_sms)
    app.include_router(customer_sms)
    app.include_router(schedule_email)
    return TestClient(app)


def _signature(token, url, params):
    text = url + ''.join(str(key) + str(params[key]) for key in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), text.encode(), hashlib.sha1).digest()).decode()


def _inbound(client, origin, token, sid, message):
    form = {'From': '+17605550111', 'To': NUMBER, 'Body': message, 'MessageSid': sid}
    return client.post('/pds/sms/twilio/inbound', data=form, headers={
        'X-Twilio-Signature': _signature(token, origin + '/pds/sms/twilio/inbound', form)})


def test_approved_sms_with_signed_consent_and_delivery_receipt(tmp_path, monkeypatch):
    origin = 'https://dispatch.example.test'
    token = 'test-secret-only'
    for key, value in {'PDS_SMS_PUBLIC_BASE_URL': origin,
                       'TWILIO_AUTH_TOKEN': token,
                       'TWILIO_ACCOUNT_SID': 'AC' + '1' * 32,
                       'PDS_TWILIO_NUMBER': NUMBER,
                       'PDS_SMS_SEND_ENABLED': 'true'}.items():
        monkeypatch.setenv(key, value)
    sid = 'SM' + '3' * 32
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'sid': sid})
    with _client(tmp_path) as client, patch('requests.post', return_value=response) as sender:
        assert _inbound(client, origin, token, 'SM' + '1' * 32, 'START').status_code == 200
        assert _inbound(client, origin, token, 'SM' + '2' * 32, 'YES').status_code == 200
        assert current_state(tmp_path, '+17605550111') == 'subscribed'
        endpoint = '/moses-action-center/pds/sms/proposals'
        payload = {'job_id': 'ticket-123', 'phone': '+17605550111',
                   'message': 'Priority Door Systems: Technician ETA 2 PM.'}
        first = client.post(endpoint, json=payload)
        assert first.status_code == 200
        pid = first.json()['proposal']['id']
        assert client.post(endpoint, json=payload).json()['proposal']['id'] == pid
        assert sender.call_count == 0
        accepted = client.post(f'{endpoint}/{pid}/decision', json={'approve': True})
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()['status'] == 'submitted'
        assert sender.call_count == 1
        assert client.post(f'{endpoint}/{pid}/decision', json={'approve': True}).status_code == 409
        form = {'MessageSid': sid, 'MessageStatus': 'delivered'}
        path = f'/pds/sms/twilio/status?proposal_id={pid}'
        confirmed = client.post(path, data=form, headers={
            'X-Twilio-Signature': _signature(token, origin + path, form)})
        assert confirmed.status_code == 200
        assert client.get(f'{endpoint}/{pid}').json()['status'] == 'delivered'
        assert _inbound(client, origin, token, 'SM' + '4' * 32, 'STOP').status_code == 200
        assert client.post(endpoint, json=payload).status_code == 409
        assert sender.call_count == 1


def test_email_approval_and_idempotent_http_path(tmp_path, monkeypatch):
    monkeypatch.setenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED', 'true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'NoReply@prioritydoors.com')
    entry = {'job_id': 'ticket-123', 'recipient': 'guest@example.test',
             'category': 'appointment', 'subject': 'Appointment update',
             'message': 'Priority Door Systems: Your technician is scheduled.'}
    with (_client(tmp_path) as client,
          patch('app.services.pds_schedule_notifications.ready'),
          patch('app.services.moses_email_transport.send_resend', return_value='resend-fake-id') as sender):
        endpoint = '/pds-schedule-notifications/email/proposals'
        first = client.post(endpoint, json=entry)
        assert first.status_code == 200, first.text
        pid = first.json()['proposal']['id']
        assert client.post(endpoint, json=entry).json()['proposal']['id'] == pid
        assert sender.call_count == 0
        accepted = client.post(f'{endpoint}/{pid}/decision', json={'approve': True})
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()['status'] == 'submitted'
        assert sender.call_count == 1
        assert client.post(f'{endpoint}/{pid}/decision', json={'approve': True}).status_code == 409
        history = client.get('/pds-schedule-notifications/jobs/ticket-123/email-history')
        assert history.status_code == 200
        assert history.json()['items'][0]['provider_id'] == 'resend-fake-id'
