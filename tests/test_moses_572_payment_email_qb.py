"""5.72: recipient lists, read-only fee planning and actual sync payload shape."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_pds_document_email as docmail
from app.services import moses_email_transport as transport
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_purchase_orders as qbpo
from app.services import pds_quickbooks_sync_preview as sync
from app.services import pds_payment_fee_plan as fees
from test_moses_569_technician_review import context, mail_identity
from test_moses_567_quickbooks_handoff import setup_request, mark_sent
from test_moses_570_quickbooks_po_hub import fixture as po_fixture


def test_multiple_to_cc_approval_and_saved_pdf(tmp_path, monkeypatch):
    request, job, record = context(tmp_path, role='office')
    monkeypatch.setattr(docmail, 'identity', mail_identity)
    proposal=docmail.propose(request,'estimate',record['number'],{
        'to':'customer@example.com; ap@example.com',
        'cc':'manager@example.com, ap@example.com'})['proposal']
    assert proposal['to_recipients']==['customer@example.com','ap@example.com']
    assert proposal['cc_recipients']==['manager@example.com']
    observed=[]
    monkeypatch.setenv('MOSES_PDS_DOCUMENT_SEND_ENABLED','true')
    monkeypatch.setattr(transport,'ready',lambda sender:None)
    monkeypatch.setattr(transport,'send_resend_attachment',lambda msg,*a,**k:observed.append(msg) or 'resend_572')
    sent=docmail.decide(request,proposal['id'],True)
    assert sent['state']=='sent'
    assert observed[0]['to']==['customer@example.com','ap@example.com']
    assert observed[0]['cc']=='manager@example.com'
    assert job['status']=='Quote Sent'
    assert docmail.history(request,'estimate',record['number'])[0]['to_recipients']==['customer@example.com','ap@example.com']


def test_invalid_addresses_and_tech_external_addresses_blocked(tmp_path,monkeypatch):
    request,job,record=context(tmp_path,role='tech')
    monkeypatch.setattr(docmail, 'identity', mail_identity)
    for address in ('foo@example.com\nBcc:evil@example.com','Alice <foo@example.com>','a@example.com; invalid'):
        with pytest.raises(HTTPException) as exc:
            docmail.propose(request,'estimate',record['number'],{'to':address})
        assert exc.value.status_code in (403,422)
    with pytest.raises(HTTPException) as exc:
        docmail.propose(request,'estimate',record['number'],{'to':'outsider@example.com'})
    assert exc.value.status_code==403
    assert not (tmp_path/'moses_pds_document_delivery_actions.json').exists()


def test_customer_contacts_exact_name_only(tmp_path,monkeypatch):
    request,job,record=context(tmp_path,role='office')
    monkeypatch.setattr(docmail, 'identity', mail_identity)
    class FakeCRM:
        def list_customers(self):return [{'id':'cust-1','company_name':'Review Test Company','invoice_email':'billing@example.com'}]
        def list_contacts(self):return [
            {'name':'Saved A','customer_id':'cust-1','email':'saved@example.com'},
            {'name':'Other','company_name':'Different Company','email':'other@example.com'}]
    request.app.state.crm_store=FakeCRM()
    view=docmail.preview(request,'invoice','JS00077') if record['type']=='invoice' else docmail.preview(request,'estimate',record['number'])
    choices={x['email'] for x in view['available_recipients']}
    assert 'saved@example.com' in choices and 'billing@example.com' in choices
    assert 'other@example.com' not in choices


def test_resend_transport_to_cc_arrays_are_strict(tmp_path,monkeypatch):
    monkeypatch.setattr(transport,'ready',lambda sender:None)
    monkeypatch.setenv('RESEND_API_KEY','re_TEST_NOT_REAL')
    captured=[]
    class FakeResponse:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,maxbytes):return b'{"id":"resend_572"}'
    def fake_open(request,timeout):
        captured.append(json.loads(request.data))
        return FakeResponse()
    monkeypatch.setattr(transport,'urlopen',fake_open)
    msg={'from':'NoReply@prioritydoors.com','to':['a@example.com','b@example.com'],
         'cc':['billing@example.com'], 'reply_to':'Invoice@prioritydoors.com',
         'subject':'Invoice JS00077','text':'Here is your invoice.'}
    ref=transport.send_resend_attachment(msg,b'%PDF-1.5\nDATA','JS00077.pdf','application/pdf',idempotency_key='a'*64)
    assert ref=='resend_572'
    assert captured[0]['to']==['a@example.com','b@example.com']
    assert captured[0]['cc']==['billing@example.com']
    msg['to']=['a@example.com','bad@example.com\r\nBcc:evil@example.com']
    with pytest.raises(HTTPException):
        transport.send_resend_attachment(msg,b'%PDF-1.5\nDATA','JS00077.pdf','application/pdf',idempotency_key='a'*64)
    assert len(captured)==1


def test_withdrawn_service_fee_is_not_billed(tmp_path):
    request,doc=setup_request(tmp_path)
    mark_sent(request)
    plan=fees.summary(request)
    assert plan['rate_percent']=='0.00' and plan['enabled_for_new_invoices'] is False
    assert {'credit_card','ach_echeck','check','cash'}.issubset(set(plan['applies_to']))
    example=fees.invoice_preview(request,'JS00021')
    assert example['existing_invoice_total']=='243.10'
    assert example['proposed_service_fee']=='0.00'
    assert example['fee_charged'] is False
    assert qb.preview(request)['invoices'][0]['total']=='243.10'
    request.state.auth_role='tech'
    for fn in (lambda:fees.summary(request),lambda:fees.invoice_preview(request,'JS00021')):
        with pytest.raises(HTTPException) as exc:fn()
        assert exc.value.status_code==403


def test_invoice_sync_preview_only_after_preparation_and_stale_changes_blocked(tmp_path):
    request,record=setup_request(tmp_path)
    mark_sent(request)
    with pytest.raises(HTTPException) as exc:sync.preview_invoice(request,'JS00021')
    assert exc.value.status_code==409
    row=qb.preview(request)['invoices'][0]
    qb.prepare(request,row['number'],row['fingerprint'])
    preview=sync.preview_invoice(request,'JS00021')
    assert preview['total']=='243.10' and preview['can_post'] is False
    assert preview['idempotency_reference']=='PDS:invoice:JS00021'
    assert [l['amount'] for l in preview['lines']]==['200.00','40.00']
    record['items'][0]['rate']=999
    with pytest.raises(HTTPException) as exc:sync.preview_invoice(request,'JS00021')
    assert exc.value.status_code==409


def test_po_sync_preview_only_after_preparation_and_vendor_mapping(tmp_path):
    request,record,source=po_fixture(tmp_path)
    row=qbpo.preview(request)['purchase_orders'][0]
    qbpo.prepare(request,row['number'],row['fingerprint'])
    preview=sync.preview_supplier_po(request,'PO-00020')
    assert preview['total']=='217.00' and preview['can_post'] is False
    assert preview['lines'][0]['amount']=='200.00'
    assert 'vendor' in preview['mapping_pending']
    record['status']='Delivered'
    source.write_text(json.dumps([record]))
    with pytest.raises(HTTPException) as exc:sync.preview_supplier_po(request,'PO-00020')
    assert exc.value.status_code==409


def test_ui_explicit_to_cc_and_fee_disabled_until_connected():
    js=(Path(__file__).parents[1]/'static/app.js').read_text()
    assert 'To (separate multiple emails with semicolons)' in js
    assert 'Add to CC' in js and 'Add to To' in js
    assert 'data-qbh-tab="payments"' in js
    assert 'No added service fee' in js


def test_invoice_description_edit_same_total_invalidates_qb_handoff(tmp_path):
    request,record=setup_request(tmp_path)
    record['items'][0]['description']='Original work description'
    mark_sent(request)
    row=qb.preview(request)['invoices'][0]
    qb.prepare(request,row['number'],row['fingerprint'])
    record['items'][0]['description']='Changed description without a price change'
    current=qb.preview(request)['invoices'][0]
    assert current['handoff_status']=='changed_since_preparation'
    with pytest.raises(HTTPException) as exc:
        sync.preview_invoice(request,'JS00021')
    assert exc.value.status_code==409


def test_duplicate_invoice_number_refuses_sync(tmp_path):
    request,record=setup_request(tmp_path)
    first=request.app.state.documents_store.list_documents
    request.app.state.documents_store.list_documents=lambda:[record,dict(record)]
    mark_sent(request)
    with pytest.raises(HTTPException) as exc:qb.preview(request)
    assert exc.value.status_code==409


def test_sent_document_cannot_be_resubmitted_to_new_recipient(tmp_path,monkeypatch):
    request,job,record=context(tmp_path,role='office')
    monkeypatch.setattr(docmail,'identity',mail_identity)
    proposal=docmail.propose(request,'estimate',record['number'])['proposal']
    monkeypatch.setenv('MOSES_PDS_DOCUMENT_SEND_ENABLED','true')
    monkeypatch.setattr(transport,'ready',lambda sender:None)
    monkeypatch.setattr(transport,'send_resend_attachment',lambda *a,**k:'resend_572')
    assert docmail.decide(request,proposal['id'],True)['state']=='sent'
    with pytest.raises(HTTPException) as exc:
        docmail.propose(request,'estimate',record['number'],{'to':'another@example.com'})
    assert exc.value.status_code==409
