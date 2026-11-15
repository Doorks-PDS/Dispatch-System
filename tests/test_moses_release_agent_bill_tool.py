"""Rev 98: live agent tool registration and approval-only bill safeguards."""
import json
import sys
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_agent


def request(tmp_path, platform='doorks'):
    return SimpleNamespace(session={'active_platform': platform},
       state=SimpleNamespace(auth_user={'id': 'test-admin'}, auth_role='office_admin'),
       app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def tools_from_agent(monkeypatch, tmp_path, platform='doorks'):
    recorded = {}
    class Agent:
        def __init__(self, **kwargs): recorded.update(kwargs)
    class Runner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            assert kwargs['max_turns'] == 5
            assert kwargs['run_config'].tracing_disabled is True
            return SimpleNamespace(final_output='Bill review requires approval.')
    class RunConfig:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=Agent, Runner=Runner, RunConfig=RunConfig, function_tool=lambda fn: fn))
    answer = moses_agent.answer(request(tmp_path, platform), 'Review a bill', [])
    assert 'approval' in answer.lower()
    return {tool.__name__: tool for tool in recorded['tools']}


def test_bill_proposal_only_in_doorks_agent(monkeypatch, tmp_path):
    assert 'propose_supplier_bill_for_approval' in tools_from_agent(monkeypatch, tmp_path, 'doorks')
    assert 'propose_supplier_bill_for_approval' not in tools_from_agent(monkeypatch, tmp_path, 'pds')
    assert 'propose_supplier_bill_for_approval' not in tools_from_agent(monkeypatch, tmp_path, 'sdc')


def test_bill_tool_is_disabled_and_changes_no_records(monkeypatch, tmp_path):
    monkeypatch.delenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED', raising=False)
    tools = tools_from_agent(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as error:
        tools['propose_supplier_bill_for_approval']('PO-TEST', 'INV-TEST', 100.0)
    assert error.value.status_code == 503
    assert list(tmp_path.rglob('*.json')) == []


def test_bill_tool_proposes_but_never_posts(monkeypatch, tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED', 'true')
    p = tmp_path/'business_workspaces'/'doorks'/'purchase_orders.json'
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps([dict(id='po1', po_number='PO-22', quantity=4, total=400,
                                   vendor='Vendor A',status='Received')]))
    j = tmp_path/'po_receiving'/'doorks'/'events.json'
    j.parent.mkdir(parents=True)
    j.write_text(json.dumps([dict(id='receipt1',po_id='po1',quantity=4)]))
    tools = tools_from_agent(monkeypatch, tmp_path)
    result = json.loads(tools['propose_supplier_bill_for_approval']('PO-22','INV-TEST',400.0))
    assert result['approval_required'] and result['executed'] is False
    assert result['payment_recorded'] is False
    assert not (p.parent/'accounting'/'supplier_bills.json').exists()
    assert len(json.loads((p.parent/'accounting'/'moses_supplier_bill_proposals.json').read_text())) == 1
