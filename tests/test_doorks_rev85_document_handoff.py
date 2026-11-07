"""Regression tests for Rev85 explicit vendor-to-office document linking."""
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.routers import doorks_portals as portal


def request(tmp_path):
    root = tmp_path / 'business_workspaces' / 'doorks'
    root.mkdir(parents=True)
    def collection(name, items):
        (root / (name + '.json')).write_text(json.dumps({'items':items}))
    collection('work_orders', [{'id':'job1','customer_id':'cust1'}])
    collection('vendor_assignments', [{'id':'a1','vendor_id':'vendor1','work_order_id':'job1'}])
    collection('customers', [{'id':'cust1'}])
    collection('estimates_invoices', [
        {'id':'office1','customer_id':'cust1','document_type':'Estimate','status':'Sent','document_number':'RE00010'},
        {'id':'office2','customer_id':'cust2','document_type':'Estimate','status':'Sent'},
        {'id':'draft','customer_id':'cust1','document_type':'Estimate','status':'Draft'},
        {'id':'invoice','customer_id':'cust1','document_type':'Invoice','status':'Sent'},
    ])
    (root / 'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[],
        'vendor_commercial_documents':[{'id':'v1','status':'approved','document_type':'estimate','assignment_id':'a1'}]}))
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
                           state=SimpleNamespace(auth_user='admin',auth_role='office_admin'),
                           session={'active_platform':'doorks'},headers={},base_url='https://example.com/')


def test_eligible_docs_scoped_by_customer_and_type(tmp_path):
    req=request(tmp_path)
    rows=portal.eligible_vendor_office_documents('v1',req)['documents']
    assert [x['id'] for x in rows] == ['office1']


def test_link_is_idempotent_and_persistent(tmp_path):
    req=request(tmp_path)
    payload=portal.VendorOfficeDocumentLink(office_document_id='office1')
    assert portal.link_vendor_proposal_to_office_document('v1',payload,req)['ok']
    assert portal.link_vendor_proposal_to_office_document('v1',payload,req)['already_linked']
    saved=portal.read(portal.store(req))['vendor_commercial_documents'][0]
    assert saved['office_document_id']=='office1'
    assert len(saved['history'])==1


@pytest.mark.parametrize('bad_id',['office2','draft','invoice'])
def test_rejects_cross_customer_draft_and_wrong_type(tmp_path,bad_id):
    req=request(tmp_path)
    with pytest.raises(HTTPException) as e:
        portal.link_vendor_proposal_to_office_document('v1',portal.VendorOfficeDocumentLink(office_document_id=bad_id),req)
    assert e.value.status_code==409


def test_requires_approved_vendor_proposal(tmp_path):
    req=request(tmp_path)
    p=portal.store(req); data=portal.read(p)
    data['vendor_commercial_documents'][0]['status']='submitted_for_review'
    portal.write(p,data)
    with pytest.raises(HTTPException) as e:
        portal.link_vendor_proposal_to_office_document('v1',portal.VendorOfficeDocumentLink(office_document_id='office1'),req)
    assert e.value.status_code==409


def test_email_rejects_non_customer_recipient(tmp_path):
    req=request(tmp_path)
    root=tmp_path/'business_workspaces'/'doorks'
    (root/'contacts.json').write_text(json.dumps({'items':[{'id':'c1','customer_id':'cust1','email':'valid@example.com'}]}))
    (root/'customers.json').write_text(json.dumps({'items':[{'id':'cust1','email':'valid@example.com'}]}))
    with pytest.raises(HTTPException) as e:
        portal.email_published_customer_document('office1',portal.OfficeDocumentEmail(
            recipient='other@example.com',subject='Estimate',message='Please review'),req)
    assert e.value.status_code==403


def test_email_requires_published_original(tmp_path):
    req=request(tmp_path)
    root=tmp_path/'business_workspaces'/'doorks'
    (root/'customers.json').write_text(json.dumps({'items':[{'id':'cust1','email':'valid@example.com'}]}))
    with pytest.raises(HTTPException) as e:
        portal.email_published_customer_document('office1',portal.OfficeDocumentEmail(
            recipient='valid@example.com',subject='Estimate',message='Please review'),req)
    assert e.value.status_code==409


def test_email_not_sent_without_smtp_configuration(tmp_path,monkeypatch):
    req=request(tmp_path)
    root=tmp_path/'business_workspaces'/'doorks'
    (root/'customers.json').write_text(json.dumps({'items':[{'id':'cust1','email':'valid@example.com'}]}))
    data=portal.read(portal.store(req))
    data['published_originals']=[{'document_id':'office1','customer_id':'cust1','file_id':'file1',
        'extension':'pdf','mime':'application/pdf','filename':'estimate.pdf'}]
    portal.write(portal.store(req),data)
    directory=root/'portal_private_uploads';directory.mkdir()
    (directory/'file1.pdf').write_bytes(b'%PDF-1.4 sample')
    for k in ('DOORKS_SMTP_HOST','DOORKS_SMTP_FROM','DOORKS_SMTP_USERNAME','DOORKS_SMTP_PASSWORD'):
        monkeypatch.delenv(k,raising=False)
    with pytest.raises(HTTPException) as e:
        portal.email_published_customer_document('office1',portal.OfficeDocumentEmail(
            recipient='valid@example.com',subject='Estimate',message='Please review'),req)
    assert e.value.status_code==503
