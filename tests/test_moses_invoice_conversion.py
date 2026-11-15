"""Approval-only conversion reuses existing workspace invoice numbering and storage."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_actions
from app.routers import doorks_assistant


def request(tmp_path, platform='sdc', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'}, auth_role=role),
                           session={'active_platform':platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path, platform='sdc'):
    base = tmp_path/'business_workspaces'/platform
    base.mkdir(parents=True, exist_ok=True)
    path=base/'estimates_invoices.json'
    original=[{'id':'est-1','document_type':'Estimate','document_number':'EST-00001',
               'status':'Approved','customer':'Example','total':175.0,'notes':'do not alter'},
              {'id':'est-2','document_type':'Estimate','document_number':'EST-00002',
               'status':'Draft','customer':'Another'}]
    path.write_text(json.dumps(original))
    return path,original


@pytest.mark.parametrize('platform,flag', [('sdc','DOORKS_SDC_MOSES_ACTIONS_ENABLED'),
                                            ('doorks','DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED')])
def test_propose_approve_invoice_confirms_existing_workflow(tmp_path,monkeypatch,platform,flag):
    monkeypatch.setenv(flag,'true')
    path,original=seed(tmp_path,platform)
    r=request(tmp_path,platform)
    proposal=moses_actions.propose_invoice(r,'est-1',platform)['proposal']
    assert json.loads(path.read_text())==original
    pending=moses_actions.pending(r,platform)['proposals']
    assert pending[0]['estimate_number']=='EST-00001'
    result=moses_actions.decide(r,proposal['id'],True,platform)
    assert result['executed'] and result['document_status']=='Draft' and not result['sent']
    docs=json.loads(path.read_text())
    assert len(docs)==3 and docs[0]==original[0]
    invoice=docs[-1]
    assert invoice['id']==result['invoice_id']
    assert invoice['source_estimate_id']=='est-1'
    assert invoice['document_number']==result['invoice_number']=='INV-00001'
    assert invoice['status']=='Draft' and invoice['notes']=='do not alter'
    with pytest.raises(HTTPException) as err:
        moses_actions.decide(r,proposal['id'],True,platform)
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:
        moses_actions.propose_invoice(r,'est-1',platform)
    assert err.value.status_code==409
    assert len(json.loads(path.read_text()))==3
    audit=json.loads((path.parent/'moses_action_audit.json').read_text())
    assert audit[0]['invoice_id']==invoice['id']


def test_rejection_stale_and_unapproved(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    path,original=seed(tmp_path)
    r=request(tmp_path)
    with pytest.raises(HTTPException) as err:
        moses_actions.propose_invoice(r,'est-2')
    assert err.value.status_code==409
    p=moses_actions.propose_invoice(r,'est-1')['proposal']
    result=moses_actions.decide(r,p['id'],False)
    assert result['state']=='rejected' and json.loads(path.read_text())==original
    p=moses_actions.propose_invoice(r,'est-1')['proposal']
    docs=json.loads(path.read_text());docs[0]['total']=300
    path.write_text(json.dumps(docs))
    with pytest.raises(HTTPException) as err:
        moses_actions.decide(r,p['id'],True)
    assert err.value.status_code==409
    assert len(json.loads(path.read_text()))==2


def test_recovery_after_invoice_write_before_proposal_finalization(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    path,_=seed(tmp_path)
    r=request(tmp_path)
    p=moses_actions.propose_invoice(r,'est-1')['proposal']
    from app.routers.workspaces import convert_estimate_to_invoice
    proposal_path=path.parent/'moses_action_proposals.json'
    rows=json.loads(proposal_path.read_text())
    rows[0]['state']='executing'
    proposal_path.write_text(json.dumps(rows))
    invoice=convert_estimate_to_invoice('sdc','est-1',r)['item']
    outcome=moses_actions.recover(r)
    assert outcome['states']['executed']==1
    assert len(json.loads(path.read_text()))==3
    assert json.loads(proposal_path.read_text())[0]['invoice_id']==invoice['id']
    assert len(json.loads((path.parent/'moses_action_audit.json').read_text()))==1


def test_workspace_and_flag_protections(tmp_path,monkeypatch):
    seed(tmp_path)
    monkeypatch.delenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED', raising=False)
    with pytest.raises(HTTPException) as err:
        moses_actions.propose_invoice(request(tmp_path),'est-1')
    assert err.value.status_code==503
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    for invalid in (request(tmp_path,'doorks'),request(tmp_path,role='technician')):
        with pytest.raises(HTTPException) as err:
            moses_actions.propose_invoice(invalid,'est-1')
        assert err.value.status_code==403
    assert len(json.loads((tmp_path/'business_workspaces'/'sdc'/'estimates_invoices.json').read_text()))==2


def test_agent_only_creates_proposal(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    path,original=seed(tmp_path)
    response=doorks_assistant._execute_invoice_tool(request(tmp_path),'sdc','est-1')
    assert response['approval_required'] and not response['executed']
    assert json.loads(path.read_text())==original
