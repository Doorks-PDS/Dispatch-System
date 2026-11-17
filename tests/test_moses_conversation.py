from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services.moses_conversation import followup

PID='b'*32
CTX={'kind':'new_work_order','proposal_id':PID,'workspace':'doorks'}

def req(workspace='doorks',role='office_admin'):
    return SimpleNamespace(session={'active_platform':workspace},state=SimpleNamespace(auth_user={'id':'test'},auth_role=role))

def scope(request):
    if request.state.auth_role!='office_admin':raise HTTPException(403,'denied')
    return request.session['active_platform']

def saved(state='executed', executed=True):
    return {'state':state,'executed':executed,'workspace':'doorks','proposal_id':PID,'requires_manual_review':False}


def test_ordinary_message_does_not_invoke_action_tools():
    assert followup(req(), 'Can you help me with a customer?',CTX) is None

def test_confirmed_work_order_and_verified_next_step():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value=saved()),patch('app.services.moses_butler_flow.next_step',return_value={'available':True,'next_kind':'estimate_draft','record_id':'wo-7'}):
        out=followup(req(),'What is next?',CTX)
    assert out['action_verified'] and out['next_action']=={'kind':'estimate_draft','record_id':'wo-7','approval_required':True}
    assert 'confirmed executed' in out['answer']

def test_unconfirmed_action_never_suggests_followup():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value=saved('pending',False)),patch('app.services.moses_butler_flow.next_step') as step:
        out=followup(req(),'Did it go through?',CTX)
    step.assert_not_called()
    assert 'next_action' not in out and 'waiting' in out['answer']

@pytest.mark.parametrize('state', ['rejected','uncertain','needs_review','executing'])
def test_nonexecuted_states_never_continue(state):
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value=saved(state,False)):
        assert 'next_action' not in followup(req(),'What happened with that action?',CTX)

def test_workspace_switch_denies_stale_context():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt') as receipt:
        out=followup(req('pds'),'What is next?',CTX)
    receipt.assert_not_called()
    assert not out['action_verified']

def test_role_guard():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope):
        with pytest.raises(HTTPException) as ex:followup(req(role='tech'),'Did it work?',CTX)
    assert ex.value.status_code==403

def test_forged_receipt_never_confirms():
    wrong={**saved(),'proposal_id':'a'*32}
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value=wrong):
        out=followup(req(),'What is next?',CTX)
    assert not out['action_verified']

def test_missing_receipt_stops_safely():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',side_effect=HTTPException(404,'not found')):
        assert not followup(req(),'Did that save?',CTX)['action_verified']

def test_bad_action_reference_not_fuzzy_matched():
    bad={**CTX,'proposal_id':'not-real'}
    assert followup(req(),'What happened?',bad)['action_verified'] is False

def test_next_step_absent_does_not_guess():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value=saved()),patch('app.services.moses_butler_flow.next_step',return_value={'available':False,'reason':'Estimate needs pricing review'}):
        out=followup(req(),'What should we do next?',CTX)
    assert 'next_action' not in out and 'pricing review' in out['answer']

def test_changed_current_record_is_not_misrepresented_as_current():
    with patch('app.services.moses_butler_flow._scope',side_effect=scope),patch('app.services.moses_butler_flow.receipt',return_value={**saved(),'current_record_matches':False}),patch('app.services.moses_butler_flow.next_step',return_value={'available':False}):
        out=followup(req(),'Did it go through?',CTX)
    assert 'underlying record has changed' in out['answer']
