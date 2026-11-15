"""Rev86: Resend server-side transport; provider is mocked, never sends mail."""
import base64
import io
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_email_transport as transport
from app.services import moses_po_delivery, moses_dispatch_send

MSG = {'from':'documents@prioritydoors.com', 'to':'customer@example.com',
       'reply_to':'Estimates@prioritydoors.com','cc':'reception@prioritydoors.com',
       'subject':'Estimate', 'text':'Please review.', 'number':'RE00076'}

def configure(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('RESEND_API_KEY','re_example_mock_only')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','documents@prioritydoors.com')

def test_resend_payload_with_pdf_and_reply_to(monkeypatch):
    configure(monkeypatch)
    captured=[]
    def fake_open(request, timeout):
        captured.append(request)
        class Reply:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'{"id":"email_mock_1"}'
        return Reply()
    monkeypatch.setattr(transport,'urlopen',fake_open)
    assert transport.send_resend(MSG, b'%PDF-1.4 mock')=='email_mock_1'
    req=captured[0]
    assert req.full_url=='https://api.resend.com/emails'
    body=json.loads(req.data)
    assert body['reply_to']=='Estimates@prioritydoors.com'
    assert body['cc']==['reception@prioritydoors.com']
    assert body['attachments'][0]['filename']=='RE00076.pdf'
    assert base64.b64decode(body['attachments'][0]['content'])==b'%PDF-1.4 mock'
    assert 're_example_mock_only' not in json.dumps(body)

def test_sender_must_match_and_no_key(monkeypatch):
    configure(monkeypatch)
    with pytest.raises(HTTPException) as ex:
        transport.ready('other@example.com')
    assert ex.value.status_code==503
    monkeypatch.delenv('RESEND_API_KEY')
    with pytest.raises(HTTPException): transport.ready(MSG['from'])

def test_reject_header_injection_and_unknown_provider(monkeypatch):
    configure(monkeypatch)
    with pytest.raises(HTTPException): transport.send_resend({**MSG,'subject':'Hi\nBcc:bad@example.com'})
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','unknown')
    with pytest.raises(HTTPException):transport.provider()

def test_resend_integrates_existing_transmit_paths(monkeypatch):
    configure(monkeypatch)
    sent=[]
    monkeypatch.setattr(transport,'send_resend',lambda msg,pdf=None:sent.append((msg,pdf)))
    moses_po_delivery._transmit(MSG,b'%PDF-1.4 mock')
    moses_dispatch_send._transmit(MSG)
    assert sent == [(MSG,b'%PDF-1.4 mock'),(MSG,None)]

def test_unconfirmed_provider_response_is_not_success(monkeypatch):
    configure(monkeypatch)
    class Reply:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self,n): return b'{}'
    monkeypatch.setattr(transport,'urlopen',lambda *a,**kw:Reply())
    with pytest.raises(RuntimeError):transport.send_resend(MSG)
