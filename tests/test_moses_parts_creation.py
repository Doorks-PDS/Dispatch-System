"""Rev 67 — approved workspace parts creation and safe recovery."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_actions
from app.routers import doorks_assistant
from app.routers.workspaces import Record,create


def req(path, platform='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'boss'},auth_role=role),
        session={'active_platform':platform},app=SimpleNamespace(state=SimpleNamespace(data_dir=path)))


def rows(tmp, platform):
    kind='inventory' if platform=='doorks' else 'products'
    p=tmp/'business_workspaces'/platform/(kind+'.json')
    return json.loads(p.read_text()) if p.exists() else []


@pytest.mark.parametrize('platform,flag', [('doorks','DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED'),('sdc','DOORKS_SDC_MOSES_ACTIONS_ENABLED')])
def test_propose_approve_reject_duplicate(tmp_path,monkeypatch,platform,flag):
    monkeypatch.setenv(flag,'true');r=req(tmp_path,platform)
    result=doorks_assistant._execute_part_tool(r,platform,'DC-100','Door closer','Acme','Supplier',
         'https://example.com/products/dc-100','https://example.com/photo.jpg',100,150)
    assert result['approval_required'] and not result['executed']
    assert rows(tmp_path,platform)==[]
    p=result['proposal']
    assert p['details']['unit_cost']=='100' and p['details']['customer_price']=='150'
    assert moses_actions.pending(r,platform)['count']==1
    done=moses_actions.decide(r,p['id'],True,platform)
    assert done['executed'] and done['part_number']=='DC-100'
    item=rows(tmp_path,platform)[0]
    assert item['source_moses_proposal_id']==p['id'] and item['image_url']=='https://example.com/photo.jpg'
    assert item['product_url']=='https://example.com/products/dc-100'
    assert len(rows(tmp_path,platform))==1
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r,p['id'],True,platform)
    assert exc.value.status_code==409
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_part(r,'dc-100','Duplicated',platform=platform)
    assert exc.value.status_code==409
    q=moses_actions.propose_part(r,'DC-101','Second part',platform=platform)['proposal']
    assert moses_actions.decide(r,q['id'],False,platform)['state']=='rejected'
    assert len(rows(tmp_path,platform))==1


def test_stale_duplicate_created_before_approval(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED','true');r=req(tmp_path)
    p=moses_actions.propose_part(r,'A-1','Closer')['proposal']
    create('doorks','inventory',Record(data={'part_number':'A-1','description':'Other'}),r)
    with pytest.raises(HTTPException) as exc:moses_actions.decide(r,p['id'],True,'doorks')
    assert exc.value.status_code==409
    assert len(rows(tmp_path,'doorks'))==1


def test_recovery_after_saved_record(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true');r=req(tmp_path,'sdc')
    p=moses_actions.propose_part(r,'SKU-7','Operator',product_url='https://example.com/sku7',platform='sdc')['proposal']
    proposal_path=tmp_path/'business_workspaces'/'sdc'/'moses_action_proposals.json'
    proposals=json.loads(proposal_path.read_text());proposals[0]['state']='executing'
    proposal_path.write_text(json.dumps(proposals))
    create('sdc','products',Record(data={**p['details'],'source_moses_proposal_id':p['id']}),r)
    report=moses_actions.recover(r,'sdc')
    assert report['states']['executed']==1 and len(rows(tmp_path,'sdc'))==1
    with pytest.raises(HTTPException):moses_actions.decide(r,p['id'],True,'sdc')
    audit=json.loads((proposal_path.parent/'moses_action_audit.json').read_text())
    assert len(audit)==1 and audit[0]['part_id']==rows(tmp_path,'sdc')[0]['id']


def test_validation_permissions_and_workspace_boundaries(tmp_path,monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED','true')
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED','true')
    r=req(tmp_path)
    for kwargs in ({'product_url':'http://example.com/a'}, {'image_url':'file:///secret'},
                   {'unit_cost':'nan'},{'customer_price':-10}):
        with pytest.raises(HTTPException) as exc:
            moses_actions.propose_part(r,'A-2','Closer',**kwargs)
        assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_part(req(tmp_path,role='technician'),'A-2','Closer')
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_part(req(tmp_path,'pds'),'A-2','Closer')
    assert exc.value.status_code==403
    moses_actions.propose_part(r,'A-2','Closer',image_url='/moses/part-image/abc')
    assert moses_actions.pending(req(tmp_path,'sdc'),'sdc')['count']==0
