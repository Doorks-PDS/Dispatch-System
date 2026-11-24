"""Moses 5.55: durable RFQ photos, email preview and explicit send approval.

Tests use fake suppliers, disposable disk paths and provider stubs. No live email.
"""
import asyncio
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException, UploadFile
import pytest
from app.routers import pds_supplier_quotes as rfq
from app.services import moses_email_transport

ROOT=Path(__file__).resolve().parents[1]


def req(tmp_path, role='lead'):
    state=SimpleNamespace(data_dir=str(tmp_path),auth_user={'id':'emp1','name':'Lead One'},auth_role=role)
    return SimpleNamespace(state=state,app=SimpleNamespace(state=state),session={'active_platform':'pds'})


def seed(tmp_path):
    folder=tmp_path/'pds_suppliers';folder.mkdir(parents=True,exist_ok=True)
    (folder/'records.json').write_text(json.dumps([{'id':'s1','name':'Door Supplier',
                                                      'email':'vendor@door.example'}]))


def upload(quote, request, filename='photo.png', data=b'\x89PNG\r\n\x1a\nminimal'):
    file=UploadFile(filename=filename,file=BytesIO(data))
    return asyncio.run(rfq.upload_quote_attachment(quote['id'],request,file,purpose='request'))


def test_new_rfq_draft_edit_preview_and_file_saved_on_durable_disk(tmp_path):
    seed(tmp_path);request=req(tmp_path)
    item=rfq.create_quote(rfq.QuoteDraft(supplier_id='s1',job_number='1126-15',
              description='36 inch storefront door',email_subject='Need storefront quote',
              email_message='Provide glass specification options.'),request)['item']
    assert item['attachments']==[] and item['status']=='draft'
    upload(item,request)
    response=rfq.list_quotes(request)['items'][0]
    assert response['attachments'][0]['filename']=='photo.png'
    assert response['attachments'][0]['purpose']=='request'
    assert (tmp_path/'pds_supplier_quotes'/'attachments'/item['id']).exists()
    preview=rfq.preview_supplier_email(item['id'],request)
    assert preview['to']=='vendor@door.example' and preview['subject']=='Need storefront quote'
    assert 'Provide glass specification options.' in preview['text']
    assert preview['attachments'][0]['size']>0 and 'content' not in preview['attachments'][0]
    changed=rfq.edit_quote_draft(item['id'],rfq.QuoteDraft(supplier_id='s1',
                    description='48 inch storefront door',job_number='1126-15'),request)['item']
    assert changed['description'].startswith('48') and changed['attachments'][0]['filename']=='photo.png'
    saved=rfq.get_quote_attachment(item['id'],changed['attachments'][0]['id'],request)
    assert saved.media_type=='image/png'
    assert saved.headers['cache-control']=='private, no-store'


def test_attachment_checks_and_permission_gates(tmp_path):
    seed(tmp_path);request=req(tmp_path)
    item=rfq.create_quote(rfq.QuoteDraft(supplier_id='s1',description='Fire door'),request)['item']
    with pytest.raises(HTTPException) as exc:
        upload(item,request,filename='../escape.png')
    assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        upload(item,request,filename='bad.pdf',data=b'not PDF')
    assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        upload(item,req(tmp_path,'tech'))
    assert exc.value.status_code==403
    upload(item,request)
    with pytest.raises(HTTPException) as exc:
        upload(item,request)
    assert exc.value.status_code==409
    too_big=UploadFile(filename='big.pdf',file=BytesIO(b'%PDF'+b'x'*(4*1024*1024)))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(rfq.upload_quote_attachment(item['id'],request,too_big,purpose='request'))
    assert exc.value.status_code==413


def test_resend_receives_exact_approved_files_and_no_double_send(tmp_path,monkeypatch):
    seed(tmp_path);request=req(tmp_path)
    item=rfq.create_quote(rfq.QuoteDraft(supplier_id='s1',description='Storefront frame'),request)['item']
    upload(item,request)
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setattr(moses_email_transport,'ready',lambda sender:None)
    messages=[]
    monkeypatch.setattr(moses_email_transport,'send_resend',lambda message: messages.append(message) or 'send_42')
    with pytest.raises(HTTPException):
        rfq.send_supplier_request(item['id'],rfq.SendDecision(approve=False),request)
    assert not messages
    result=rfq.send_supplier_request(item['id'],rfq.SendDecision(approve=True),request)
    assert result['state']=='accepted_by_provider' and result['item']['status']=='awaiting_supplier'
    assert len(messages)==1 and messages[0]['to']=='vendor@door.example'
    assert messages[0]['reply_to']=='reception@prioritydoors.com'
    assert messages[0]['attachments'][0]['content'].startswith(b'\x89PNG')
    with pytest.raises(HTTPException) as exc:
        rfq.send_supplier_request(item['id'],rfq.SendDecision(approve=True),request)
    assert exc.value.status_code==409
    with pytest.raises(HTTPException) as exc:
        upload(item,request)
    assert exc.value.status_code==409
    reply=UploadFile(filename='vendor_quote.pdf',file=BytesIO(b'%PDF-1.4\n%%EOF'))
    saved=asyncio.run(rfq.upload_quote_attachment(item['id'],request,reply,purpose='response'))
    assert saved['attachment']['purpose']=='response'
    received=rfq.update_quote(item['id'],rfq.QuoteUpdate(status='quote_received',
          supplier_quote_number='Q-100',supplier_cost=350,lead_time='2 weeks'),request)['item']
    assert received['status']=='quote_received' and len(received['attachments'])==2


def test_resend_transport_encodes_multiple_attached_files(tmp_path,monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setenv('RESEND_API_KEY','re_fake_provider_test')
    captured=[]
    class FakeResponse:
        status=200
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def read(self,_size):return b'{"id":"send_123"}'
    def fake_urlopen(request,timeout):
        captured.append(json.loads(request.data.decode('utf-8')))
        return FakeResponse()
    monkeypatch.setattr(moses_email_transport,'urlopen',fake_urlopen)
    sender={'from':'NoReply@prioritydoors.com','to':'vendor@door.example',
            'reply_to':'reception@prioritydoors.com','subject':'RFQ','text':'Quote this',
            'attachments':[{'filename':'drawing.pdf','mime':'application/pdf','content':b'%PDF-test'},
                          {'filename':'photo.png','mime':'image/png','content':b'\x89PNG\r\n\x1a\ntest'}]}
    assert moses_email_transport.send_resend(sender)=='send_123'
    assert len(captured[0]['attachments'])==2
    assert captured[0]['attachments'][0]['filename']=='drawing.pdf'
    assert 'content' not in json.dumps(sender['attachments'][0],default=str) or isinstance(sender['attachments'][0]['content'],bytes)


def test_job_flow_supplier_queue_is_same_saved_rfq_flow():
    js=(ROOT/'static/app.js').read_text()
    flow=js[js.index('async function openPdsJobFlowWorkQueue()'):js.index('function renderJobFlowView(')]
    for snippet in ('Supplier Pricing', 'Request Supplier Quote', 'Review Email & Send',
                    '/email-preview', '/attachments', 'Record Supplier Response',
                    'Approve & Send via Resend','await reloadQuotes()'):
        assert snippet in flow
    assert 'apiUpdateJob(' not in flow
    assert 'new WebSocket(' not in flow
    assert "reply_to" in (ROOT/'app/routers/pds_supplier_quotes.py').read_text()
