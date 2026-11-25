"""Exercise signed Twilio keyword webhooks against the real FastAPI routes.

No provider calls, production credentials, or persistent PDS records are used.
"""
import base64
import hashlib
import hmac
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.pds_sms import router as sms_router
from app.services.pds_sms_consent import NUMBER, current_state


def _app(tmp_path):
    """Isolated application: no shared main.app state or production data writes."""
    app = FastAPI()
    app.state.data_dir = str(tmp_path)
    app.include_router(sms_router)
    return app


def _signature(token, url, params):
    base = url + ''.join(str(key) + str(params[key]) for key in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), base.encode(), hashlib.sha1).digest()).decode()


def _post(client, root, token, sender, sid, body):
    params = {'From': sender, 'To': NUMBER, 'Body': body, 'MessageSid': sid}
    return client.post('/pds/sms/twilio/inbound', data=params,
                       headers={'X-Twilio-Signature': _signature(token, root+'/pds/sms/twilio/inbound', params)})


def test_signed_start_yes_stop_flow_is_durable_and_idempotent(monkeypatch, tmp_path):
    base = 'https://pds.example.test'
    token = 'test-token-only'
    sender = '+17605550135'
    app = _app(tmp_path)
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', base)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', token)
    with TestClient(app) as client:
        start = _post(client, base, token, sender, 'SM'+'1'*32, 'START')
        assert start.status_code == 200
        assert 'Reply YES' in start.text
        assert current_state(tmp_path, sender) == 'pending'

        # Retransmission must replay the same response, not create a new state change.
        repeat = _post(client, base, token, sender, 'SM'+'1'*32, 'START')
        assert repeat.status_code == 200
        assert repeat.text == start.text

        yes = _post(client, base, token, sender, 'SM'+'2'*32, 'YES')
        assert yes.status_code == 200
        assert current_state(tmp_path, sender) == 'subscribed'

        stop = _post(client, base, token, sender, 'SM'+'3'*32, 'STOP')
        assert stop.status_code == 200
        assert current_state(tmp_path, sender) == 'unsubscribed'

        after_stop = _post(client, base, token, sender, 'SM'+'4'*32, 'YES')
        assert after_stop.status_code == 200
        assert current_state(tmp_path, sender) == 'unsubscribed'


def test_signed_webhook_rejects_changed_message_and_wrong_destination(monkeypatch, tmp_path):
    base='https://pds.example.test'
    token='local-test-token'
    sender='+17605550136'
    app = _app(tmp_path)
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', base)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', token)
    with TestClient(app) as client:
        params={'From':sender,'To':NUMBER,'Body':'START','MessageSid':'SM'+'5'*32}
        sig=_signature(token,base+'/pds/sms/twilio/inbound',params)
        tampered=dict(params,Body='STOP')
        bad=client.post('/pds/sms/twilio/inbound',data=tampered,headers={'X-Twilio-Signature':sig})
        assert bad.status_code==403
        assert current_state(tmp_path,sender)=='unknown'

        wrong=dict(params,To='+17605550199')
        sig_wrong=_signature(token,base+'/pds/sms/twilio/inbound',wrong)
        rejected=client.post('/pds/sms/twilio/inbound',data=wrong,
                             headers={'X-Twilio-Signature':sig_wrong})
        assert rejected.status_code==403
        assert current_state(tmp_path,sender)=='unknown'


def test_advanced_opt_out_records_consent_without_duplicate_reply(monkeypatch, tmp_path):
    base = 'https://pds.example.test'
    token = 'test-token-advanced'
    sender = '+17605550137'
    app = _app(tmp_path)
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', base)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', token)
    with TestClient(app) as client:
        def send(body, kind, sid):
            params = {'From': sender, 'To': NUMBER, 'Body': body,
                      'MessageSid': 'SM' + sid * 32, 'OptOutType': kind}
            return client.post('/pds/sms/twilio/inbound', data=params,
                               headers={'X-Twilio-Signature': _signature(
                                   token, base + '/pds/sms/twilio/inbound', params)})

        start = send('UNSTOP', 'START', 'a')
        assert start.status_code == 200
        assert start.text == '<Response/>'
        assert current_state(tmp_path, sender) == 'pending'

        yes = _post(client, base, token, sender, 'SM' + 'b' * 32, 'YES')
        assert yes.status_code == 200
        assert current_state(tmp_path, sender) == 'subscribed'

        help_response = send('HELP', 'HELP', 'c')
        assert help_response.text == '<Response/>'
        assert current_state(tmp_path, sender) == 'subscribed'

        stop = send('STOP', 'STOP', 'd')
        assert stop.text == '<Response/>'
        assert current_state(tmp_path, sender) == 'unsubscribed'
        repeat = send('STOP', 'STOP', 'd')
        assert repeat.text == '<Response/>'
        assert current_state(tmp_path, sender) == 'unsubscribed'

        invalid = send('START', 'INVALID', 'e')
        assert invalid.status_code == 400
        assert current_state(tmp_path, sender) == 'unsubscribed'
