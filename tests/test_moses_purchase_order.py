"""Moses: approved, durable draft purchase-order creation via the normal workspace service."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_actions
from app.routers import doorks_assistant


def req(tmp_path, platform='sdc', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'}, auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path, platform):
    base = tmp_path/'business_workspaces'/platform
    base.mkdir(parents=True, exist_ok=True)
    (base/'vendors.json').write_text(json.dumps([{'id':'vendor-1','name':'Supplier A','active':True}]))
    return base


@pytest.mark.parametrize('platform,flag', [('sdc','DOORKS_SDC_MOSES_ACTIONS_ENABLED'),
                                            ('doorks','DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED')])
def test_create_draft_po_only_after_approval(tmp_path, monkeypatch, platform, flag):
    monkeypatch.setenv(flag, 'true')
    base=seed(tmp_path, platform)
    r=req(tmp_path, platform)
    response=doorks_assistant._execute_purchase_order_tool(r,platform,'vendor-1','Commercial door closer',2,125)
    assert response['approval_required'] and not response['executed']
    assert not (base/'purchase_orders.json').exists()
    proposal=response['proposal']
    assert proposal['details']['amount']=='250.00'
    assert moses_actions.pending(r,platform)['proposals'][0]['details']['vendor']=='Supplier A'
    result=moses_actions.decide(r,proposal['id'],True,platform)
    assert result['executed'] and not result['sent'] and result['po_number']=='PO-00001'
    rows=json.loads((base/'purchase_orders.json').read_text())
    assert len(rows)==1 and rows[0]['status']=='Draft'
    assert rows[0]['source_moses_proposal_id']==proposal['id']
    assert rows[0]['vendor_id']=='vendor-1'
    with pytest.raises(HTTPException) as err:
        moses_actions.decide(r,proposal['id'],True,platform)
    assert err.value.status_code==409
    assert len(json.loads((base/'purchase_orders.json').read_text()))==1
    assert json.loads((base/'moses_action_audit.json').read_text())[0]['po_id']==rows[0]['id']


def test_reject_stale_and_invalid_values(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    base=seed(tmp_path,'sdc');r=req(tmp_path)
    for q,c in [(0,1),(1,-1),('nan',2),('inf',1),(1,'nan')]:
        with pytest.raises(HTTPException):moses_actions.propose_purchase_order(r,'vendor-1','Closer',q,c)
    proposal=moses_actions.propose_purchase_order(r,'vendor-1','Closer',1,50)['proposal']
    assert moses_actions.decide(r,proposal['id'],False)['state']=='rejected'
    assert not (base/'purchase_orders.json').exists()
    proposal=moses_actions.propose_purchase_order(r,'vendor-1','Closer',1,50)['proposal']
    vendor_path=base/'vendors.json'; rows=json.loads(vendor_path.read_text());rows[0]['name']='Changed Name';vendor_path.write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as err:moses_actions.decide(r,proposal['id'],True)
    assert err.value.status_code==409
    assert not (base/'purchase_orders.json').exists()


def test_crash_recovery_preserves_single_po(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    base=seed(tmp_path,'sdc');r=req(tmp_path)
    proposal=moses_actions.propose_purchase_order(r,'vendor-1','Closer',1,50)['proposal']
    p=base/'moses_action_proposals.json';rows=json.loads(p.read_text());rows[0]['state']='executing';p.write_text(json.dumps(rows))
    from app.routers.workspaces import create,Record
    create('sdc','purchase_orders',Record(data={**proposal['details'],'status':'Draft','source_moses_proposal_id':proposal['id']}),r)
    recovery=moses_actions.recover(r)
    assert recovery['states']['executed']==1
    assert len(json.loads((base/'purchase_orders.json').read_text()))==1
    with pytest.raises(HTTPException):moses_actions.decide(r,proposal['id'],True)
    assert len(json.loads((base/'moses_action_audit.json').read_text()))==1


def test_cross_platform_and_disabled(tmp_path,monkeypatch):
    seed(tmp_path,'sdc')
    monkeypatch.delenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED',raising=False)
    with pytest.raises(HTTPException) as err:moses_actions.propose_purchase_order(req(tmp_path),'vendor-1','Closer',1,50)
    assert err.value.status_code==503
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    for r in [req(tmp_path,'pds'),req(tmp_path,role='technician')]:
        with pytest.raises(HTTPException) as err:moses_actions.propose_purchase_order(r,'vendor-1','Closer',1,50)
        assert err.value.status_code==403
