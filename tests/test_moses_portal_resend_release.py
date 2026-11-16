"""Moses Resend customer-original handoff: only synthetic test records/provider mocks."""
import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from app.routers import doorks_portals as portal
from app.services import moses_email_transport as transport
from tests.test_doorks_rev85_document_handoff import request


def configured(tmp_path, monkeypatch):
    req=request(tmp_path)
    root=tmp_path/'business_workspaces'/'doorks'
    (root/'customers.json').write_text(json.dumps({'items':[{'id':'cust1','email':'test-customer@example.com'}]}))
    data=portal.read(portal.store(req))
    data['published_originals']=[{'document_id':'office1','customer_id':'cust1',
        'file_id':'file1','extension':'pdf','mime':'application/pdf','filename':'estimate.pdf'}]
    portal.write(portal.store(req),data)
    folder=root/'portal_private_uploads';folder.mkdir()
    (folder/'file1.pdf').write_bytes(b'%PDF-1.4 synthetic only')
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setenv('MOSES_ESTIMATES_REPLY_TO','reception@prioritydoors.com')
    monkeypatch.setenv('RESEND_API_KEY','re_synthetic_test_not_a_real_key')
    return req


def payload():
    return portal.OfficeDocumentEmail(recipient='test-customer@example.com',
                                       subject='Approved estimate',message='Please review the attached estimate.')


def test_portal_uses_resend_acceptance_and_blocks_duplicate(tmp_path,monkeypatch):
    req=configured(tmp_path,monkeypatch)
    calls=[]
    class Reply:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,n):return b'{"id":"email_test_123"}'
    def fake_open(request,timeout):
        calls.append(request)
        return Reply()
    monkeypatch.setattr(transport,'urlopen',fake_open)
    response=portal.email_published_customer_document('office1',payload(),req)
    assert response['provider']=='resend'
    assert response['delivery_status']=='accepted_by_provider'
    assert len(calls)==1
    assert calls[0].full_url=='https://api.resend.com/emails'
    outgoing=json.loads(calls[0].data)
    assert outgoing['from']=='NoReply@prioritydoors.com'
    assert outgoing['reply_to']=='reception@prioritydoors.com'
    assert outgoing['to']==['test-customer@example.com']
    assert outgoing['attachments'][0]['filename']=='estimate.pdf'
    rows=portal.read(portal.store(req))['document_email_history']
    assert len(rows)==1 and rows[0]['state']=='accepted_by_provider'
    assert rows[0]['provider_message_id']=='email_test_123'
    with pytest.raises(HTTPException) as error:
        portal.email_published_customer_document('office1',payload(),req)
    assert error.value.status_code==409
    assert len(calls)==1


def test_portal_uncertain_resend_send_stays_on_manual_review(tmp_path,monkeypatch):
    req=configured(tmp_path,monkeypatch)
    def fail(*args,**kwargs):raise TimeoutError()
    monkeypatch.setattr(transport,'urlopen',fail)
    with pytest.raises(HTTPException) as error:
        portal.email_published_customer_document('office1',payload(),req)
    assert error.value.status_code==502
    rows=portal.read(portal.store(req))['document_email_history']
    assert len(rows)==1 and rows[0]['state']=='needs_review'
    with pytest.raises(HTTPException) as error:
        portal.email_published_customer_document('office1',payload(),req)
    assert error.value.status_code==409


def test_portal_requires_resend_and_does_not_fall_back_to_outlook(tmp_path,monkeypatch):
    req=configured(tmp_path,monkeypatch)
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','smtp')
    for key in ('DOORKS_SMTP_HOST','DOORKS_SMTP_USERNAME',
                'DOORKS_SMTP_PASSWORD','DOORKS_SMTP_FROM'):
        monkeypatch.setenv(key,'fake-legacy-smtp-value')
    called=[]
    monkeypatch.setattr(transport,'urlopen',lambda *a,**k:called.append(True))
    with pytest.raises(HTTPException):
        portal.email_published_customer_document('office1',payload(),req)
    assert not called
    # An intent might have been written, but no send has occurred.
    assert portal.read(portal.store(req))['document_email_history'][0]['state']=='needs_review'
