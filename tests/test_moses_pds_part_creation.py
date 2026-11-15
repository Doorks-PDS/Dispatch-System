"""Rev 68 — PDS part creation stays approval-only and within PDS's catalog."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_pds_parts
from app.routers import doorks_assistant, data


def req(tmp_path, platform='pds', role='office_admin'):
    state=SimpleNamespace(data_dir=tmp_path,project_root=tmp_path,
                          auth_user={'id':'office'},auth_role=role)
    return SimpleNamespace(state=state,app=SimpleNamespace(state=state),
                           session={'active_platform':platform})


def catalog(request):
    return data._read_json_file(data._parts_path(request), {'items': []})['items']


def test_pds_part_approval_duplicate_rejection(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED','true')
    monkeypatch.setattr(data, '_parts_path', lambda r:tmp_path/'pds_parts.json')
    r=req(tmp_path)
    proposed=doorks_assistant._execute_pds_part_tool(r,'4040XP','Door closer','LCN',
        'Supplier','https://example.com/item','https://example.com/p.jpg',225)
    assert proposed['approval_required'] and not proposed['executed']
    assert catalog(r)==[]
    p=proposed['proposal']
    assert moses_pds_parts.pending(r)['count']==1
    created=doorks_assistant.decide_pds_action(p['id'], doorks_assistant.MosesDecision(approve=True), r)
    assert created['executed'] and catalog(r)[0]['price']==225
    assert catalog(r)[0]['product_url']=='https://example.com/item'
    with pytest.raises(HTTPException) as exc:
        doorks_assistant.decide_pds_action(p['id'],doorks_assistant.MosesDecision(approve=True),r)
    assert exc.value.status_code==409
    with pytest.raises(HTTPException) as exc:
        moses_pds_parts.propose(r,'4040xp','Duplicate')
    assert exc.value.status_code==409
    rejected=moses_pds_parts.propose(r,'AB12','Second')['proposal']
    assert moses_pds_parts.decide(r,rejected['id'],False)['state']=='rejected'
    assert len(catalog(r))==1


def test_pds_part_reject_stale_duplicate_and_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED','true')
    monkeypatch.setattr(data, '_parts_path', lambda r:tmp_path/'pds_parts.json')
    r=req(tmp_path)
    p=moses_pds_parts.propose(r,'A10','Original')['proposal']
    data.create_part(r,data.PartPayload(part_number='A10',description='Manual creation'),None)
    with pytest.raises(HTTPException) as exc:
        moses_pds_parts.decide(r,p['id'],True)
    assert exc.value.status_code==409
    assert len(catalog(r))==1
    for bad in [req(tmp_path,'sdc'),req(tmp_path,'pds','field_tech')]:
        with pytest.raises(HTTPException) as exc:
            moses_pds_parts.propose(bad,'A12','Not authorized')
        assert exc.value.status_code==403
    with pytest.raises(HTTPException):
        moses_pds_parts.propose(r,'A12','Unsafe image',image_url='http://example.com/img')


def test_pds_part_interrupted_save_quarantined(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED','true')
    monkeypatch.setattr(data, '_parts_path', lambda r:tmp_path/'pds_parts.json')
    r=req(tmp_path)
    p=moses_pds_parts.propose(r,'PART-1','Operator')['proposal']
    original=data.create_part
    def interrupted(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Simulated interrupted confirmation')
    monkeypatch.setattr(data,'create_part',interrupted)
    with pytest.raises(HTTPException) as exc:
        moses_pds_parts.decide(r,p['id'],True)
    assert exc.value.status_code==500
    assert len(catalog(r))==1
    assert moses_pds_parts.pending(r)['proposals'][0]['state']=='needs_review'
    with pytest.raises(HTTPException) as exc:
        moses_pds_parts.decide(r,p['id'],True)
    assert exc.value.status_code==409


def test_pds_parts_disabled_by_default(tmp_path,monkeypatch):
    monkeypatch.delenv('DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED',raising=False)
    with pytest.raises(HTTPException) as exc:
        moses_pds_parts.propose(req(tmp_path),'PART','Description')
    assert exc.value.status_code==503
