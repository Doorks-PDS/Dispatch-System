"""No production writes: exercise the unified Butler guard and receipt contract."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_butler_flow as flow


def _request(platform='pds',role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'tester'},auth_role=role),
                           session={'active_platform':platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir='/tmp/moses-butter-no-data')))


def test_workspace_capability_matrix_is_scoped():
    assert 'job_status' in flow.capabilities(_request('pds'))['actions']
    assert 'supplier_bill' in flow.capabilities(_request('doorks'))['actions']
    assert 'supplier_bill' not in flow.capabilities(_request('sdc'))['actions']
    assert flow.capabilities(_request())['chat_can_approve'] is False


def test_non_admin_and_cross_workspace_fail_closed():
    with pytest.raises(HTTPException) as e:
        flow.prepare(_request('pds','technician'),'job_status','pds-1',{'new_status':'Complete'})
    assert e.value.status_code==403
    with pytest.raises(HTTPException) as e:
        flow.prepare(_request('pds'),'supplier_bill','po-1',{})
    assert e.value.status_code==403


def test_strict_action_arguments_and_exact_identity():
    req=_request('pds')
    with pytest.raises(HTTPException) as e:
        flow.prepare(req,'job_status',' pds-1 ',{'new_status':'Complete'})
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:
        flow.prepare(req,'job_status','pds-1',{'new_status':'Complete','delete_everything':True})
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:
        flow.prepare(req,'job_status','pds-1',{})
    assert e.value.status_code==422


def test_proposal_only_and_saved_receipt(monkeypatch):
    from app.services import moses_pds_actions
    monkeypatch.setattr(flow,'_confirm_target',lambda *args: None)
    monkeypatch.setattr(moses_pds_actions,'propose',lambda req,rid,status:{'proposal':{'id':'f'*32},'executed':False,'approval_required':True})
    result=flow.prepare(_request('pds'),'job_status','pds-1',{'new_status':'Complete'})
    assert result['proposal_id']=='f'*32
    assert result['executed'] is False and result['approval_required'] is True
    monkeypatch.setattr(flow,'_proposal',lambda *args:{'id':'f'*32,'state':'pending','record_id':'pds-1'})
    pending=flow.receipt(_request('pds'),'job_status','f'*32)
    assert pending['executed'] is False and pending['state']=='pending'
    monkeypatch.setattr(flow,'_proposal',lambda *args:{'id':'f'*32,'state':'executed','record_id':'pds-1','confirmed_at':'today'})
    complete=flow.receipt(_request('pds'),'job_status','f'*32)
    assert complete['executed'] is True and complete['confirmed_at']=='today'


def test_reject_fake_proposal_receipt(monkeypatch):
    from app.services import moses_pds_actions
    monkeypatch.setattr(flow,'_confirm_target',lambda *args: None)
    monkeypatch.setattr(moses_pds_actions,'propose',lambda *args:{'proposal':{'id':'f'*32},'executed':True,'approval_required':False})
    with pytest.raises(HTTPException) as e:
        flow.prepare(_request('pds'),'job_status','pds-1',{'new_status':'Complete'})
    assert e.value.status_code==500


def test_bad_approval_payload_does_not_trigger_backend(monkeypatch):
    with pytest.raises(HTTPException) as e:
        flow.decide(_request('pds'),'job_status','f'*32,'yes')
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:
        flow.decide(_request('pds','technician'),'job_status','f'*32,True)
    assert e.value.status_code==403


def test_receipt_looks_up_exact_kind_workspace_and_id(monkeypatch):
    from app.services import moses_pds_actions
    monkeypatch.setattr(moses_pds_actions,'_file',lambda req:'not-used')
    monkeypatch.setattr(moses_pds_actions,'_read',lambda path:[{'id':'f'*32,'kind':'pds_job_status','state':'executed','record_id':'pds-1'}])
    assert flow.receipt(_request('pds'),'job_status','f'*32)['executed'] is True
    with pytest.raises(HTTPException):
        flow.receipt(_request('pds'),'job_status','e'*32)


def test_human_decision_returns_confirmed_saved_receipt(monkeypatch):
    from app.services import moses_pds_actions
    calls=[]
    def decide_stub(req,pid,approved):
        calls.append((pid,approved))
        return {'executed':True,'proposal_id':pid,'state':'executed'}
    monkeypatch.setattr(moses_pds_actions,'decide',decide_stub)
    states=iter([{'executed':False, 'state':'pending'},
                 {'executed':True,'state':'executed', 'proposal_id':'f'*32}])
    monkeypatch.setattr(flow,'receipt',lambda *args: next(states))
    result=flow.decide(_request('pds'),'job_status','f'*32,True)
    assert calls==[('f'*32,True)]
    assert result['executed'] is True


def test_decision_disagrees_with_saved_ledger_fails_closed(monkeypatch):
    from app.services import moses_pds_actions
    monkeypatch.setattr(moses_pds_actions,'decide',lambda *args:{'executed':True})
    monkeypatch.setattr(flow,'receipt',lambda *args:{'executed':False,'state':'pending'})
    with pytest.raises(HTTPException) as exc:
        flow.decide(_request('pds'),'job_status','f'*32,True)
    assert exc.value.status_code==500
