"""Rev74: zero live emails; the SMTP transport is replaced in tests."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_po_delivery as service


def setup(tmp_path, monkeypatch, platform='doorks'):
    for k,v in {'MOSES_PO_SEND_ENABLED':'true','MOSES_DOCUMENTS_FROM':'office@example.com',
                'MOSES_PURCHASING_REPLY_TO':'purchasing@example.com','DOORKS_SMTP_FROM':'office@example.com',
                'DOORKS_SMTP_HOST':'smtp.example.com','DOORKS_SMTP_USERNAME':'test',
                'DOORKS_SMTP_PASSWORD':'test'}.items():monkeypatch.setenv(k,v)
    record={'id':'po1','po_number':'PO-00123','vendor':'Vendor Co','supplier_id':'vendor1',
            'description':'Two door closers','quantity':2,'unit_cost':125,'total':250,'status':'Draft'}
    if platform=='pds':
        folder=tmp_path/'pds_purchase_orders';folder.mkdir(parents=True)
        (folder/'records.json').write_text(json.dumps([record]))
        vendors=tmp_path/'pds_suppliers';vendors.mkdir(parents=True)
        (vendors/'records.json').write_text(json.dumps([{'id':'vendor1','name':'Vendor Co','email':'ap@vendor.example'}]))
        path=folder/'records.json'
    else:
        folder=tmp_path/'business_workspaces'/platform;folder.mkdir(parents=True)
        (folder/'purchase_orders.json').write_text(json.dumps([record]))
        (folder/'vendors.json').write_text(json.dumps([{'id':'vendor1','name':'Vendor Co','email':'ap@vendor.example'}]))
        path=folder/'purchase_orders.json'
    req=SimpleNamespace(state=SimpleNamespace(auth_user='admin',auth_role='office_admin'),
                        session={'active_platform':platform},
                        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))
    return req,path,record

@pytest.mark.parametrize('platform',['doorks','sdc','pds'])
def test_approved_po_sends_pdf_once(tmp_path,monkeypatch,platform):
    req,path,record=setup(tmp_path,monkeypatch,platform)
    sent=[]
    monkeypatch.setattr(service,'_transmit',lambda snap,pdf:sent.append((snap, pdf)))
    p=service.propose(req,platform,'po1')['proposal']
    assert not sent
    assert p['to']=='ap@vendor.example'
    response=service.decide(req,platform,p['id'],True)
    assert response['sent'] and len(sent)==1
    assert sent[0][1].startswith(b'%PDF')
    assert sent[0][0]['number']=='PO-00123'
    with pytest.raises(HTTPException):service.decide(req,platform,p['id'],True)
    with pytest.raises(HTTPException):service.propose(req,platform,'po1')
    assert service.history(req,platform,'po1')[0]['state']=='sent'

def test_reject_and_changed_total(tmp_path,monkeypatch):
    req,path,record=setup(tmp_path,monkeypatch)
    proposal=service.propose(req,'doorks','po1')['proposal']
    assert service.decide(req,'doorks',proposal['id'],False)['state']=='rejected'
    proposal=service.propose(req,'doorks','po1')['proposal']
    record['total']=300
    path.write_text(json.dumps([record]))
    with pytest.raises(HTTPException) as e:service.decide(req,'doorks',proposal['id'],True)
    assert e.value.status_code==409
    assert service.history(req,'doorks','po1')[-1]['state']=='stale'

def test_uncertain_outcome_must_not_retry(tmp_path,monkeypatch):
    req,path,record=setup(tmp_path,monkeypatch)
    proposal=service.propose(req,'doorks','po1')['proposal']
    monkeypatch.setattr(service,'_transmit',lambda snap,pdf: (_ for _ in ()).throw(TimeoutError()))
    assert service.decide(req,'doorks',proposal['id'],True)['state']=='uncertain'
    with pytest.raises(HTTPException):service.propose(req,'doorks','po1')
    record['notes']='Edited after ambiguous SMTP result'
    path.write_text(json.dumps([record]))
    with pytest.raises(HTTPException):service.propose(req,'doorks','po1')

def test_disabled_workspace_and_missing_fields(tmp_path,monkeypatch):
    req,path,record=setup(tmp_path,monkeypatch)
    req.session['active_platform']='pds'
    with pytest.raises(HTTPException) as e:service.propose(req,'doorks','po1')
    assert e.value.status_code==403
    req.session['active_platform']='doorks'
    monkeypatch.delenv('MOSES_PO_SEND_ENABLED')
    with pytest.raises(HTTPException) as e:service.propose(req,'doorks','po1')
    assert e.value.status_code==503
    monkeypatch.setenv('MOSES_PO_SEND_ENABLED','true')
    record['total']='';path.write_text(json.dumps([record]))
    with pytest.raises(HTTPException) as e:service.propose(req,'doorks','po1')
    assert e.value.status_code==409

def test_invalid_supplier_recipient_blocks(tmp_path,monkeypatch):
    req,path,record=setup(tmp_path,monkeypatch)
    vendor_path=path.parent/'vendors.json'
    vendor_path.write_text(json.dumps([{'id':'vendor1','email':'bad-address'}]))
    with pytest.raises(HTTPException):service.propose(req,'doorks','po1')
