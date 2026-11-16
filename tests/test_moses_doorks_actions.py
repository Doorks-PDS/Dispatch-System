"""Rev 55: bounded, approval-only Doorks work order action integration."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services import moses_actions, moses_agent
from app.routers import doorks_assistant as assistant


def req(tmp_path, platform='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'admin-1'}, auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path):
    path = tmp_path / 'business_workspaces' / 'doorks' / 'work_orders.json'
    path.parent.mkdir(parents=True)
    original = [{'id': 'wo-1', 'job_number': '1126-01', 'customer': 'Example Customer',
                 'status': 'Dispatch', 'address': 'Example Address', 'notes': 'untouched'},
                {'id': 'wo-2', 'job_number': '1126-02', 'customer': 'Other Customer', 'status': 'Scheduled'}]
    path.write_text(json.dumps(original))
    return path, original


def test_proposal_then_approve_verifies_saved_work_order(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    proposal = assistant.propose_work_order_status(
        assistant.MosesWorkOrderProposal(record_id='wo-1', new_status='Scheduled'), r)
    assert proposal['executed'] is False and proposal['approval_required']
    assert json.loads(path.read_text()) == original
    queue = assistant.pending_work_order_actions(r)
    assert queue['proposals'][0]['id'] == proposal['proposal']['id']
    result = assistant.decide_work_order_action(proposal['proposal']['id'], assistant.MosesDecision(approve=True), r)
    assert result['state'] == 'executed' and result['confirmed_status'] == 'Scheduled'
    assert json.loads(path.read_text())[0]['status'] == 'Scheduled'
    assert json.loads(path.read_text())[0]['notes'] == 'untouched'
    audit_path = path.parent / 'moses_action_audit.json'
    audit = json.loads(audit_path.read_text())
    assert audit[0]['kind'] == 'doorks_work_order_status'
    with pytest.raises(HTTPException) as error:
        assistant.decide_work_order_action(proposal['proposal']['id'], assistant.MosesDecision(approve=True), r)
    assert error.value.status_code == 409


def test_work_order_rejection_never_changes_record(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    p = moses_actions.propose(r, 'wo-1', 'Cancelled', platform='doorks')['proposal']
    result = moses_actions.decide(r, p['id'], False, platform='doorks')
    assert result['state'] == 'rejected' and not result['executed']
    assert json.loads(path.read_text()) == original


def test_work_order_stale_and_missing_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, _ = seed(tmp_path)
    r = req(tmp_path)
    p = moses_actions.propose(r, 'wo-1', 'Complete', platform='doorks')['proposal']
    current = json.loads(path.read_text())
    current[0]['status'] = 'In Progress'
    path.write_text(json.dumps(current))
    with pytest.raises(HTTPException) as error:
        moses_actions.decide(r, p['id'], True, platform='doorks')
    assert error.value.status_code == 409
    assert json.loads(path.read_text())[0]['status'] == 'In Progress'
    with pytest.raises(HTTPException) as error:
        moses_actions.propose(r, 'missing', 'Complete', platform='doorks')
    assert error.value.status_code == 404


def test_work_order_guards_and_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', raising=False)
    path, original = seed(tmp_path)
    with pytest.raises(HTTPException) as error:
        moses_actions.propose(req(tmp_path), 'wo-1', 'Scheduled', platform='doorks')
    assert error.value.status_code == 503
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    for platform, role in [('sdc', 'office_admin'), ('doorks', 'technician')]:
        with pytest.raises(HTTPException) as error:
            moses_actions.propose(req(tmp_path, platform, role), 'wo-1', 'Scheduled', platform='doorks')
        assert error.value.status_code == 403
    assert json.loads(path.read_text()) == original


def test_work_order_search_is_bounded_and_proposal_only(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    results = assistant._execute_doorks_tool(r, 'search_work_orders', {'query': 'Example'})
    assert results['matching_count'] == 1 and results['examples'][0]['id'] == 'wo-1'
    assert 'notes' not in results['examples'][0]
    proposed = assistant._execute_doorks_tool(r, 'propose_work_order_status', {'record_id': 'wo-1', 'new_status': 'In Progress'})
    assert proposed['approval_required'] and proposed['executed'] is False
    assert json.loads(path.read_text()) == original
    assert assistant._execute_doorks_tool(r, 'delete_work_order')['error'] == 'Tool is not authorized'
    assert assistant._execute_doorks_tool(r, 'propose_work_order_status', {'record_id': 'wo-1', 'new_status': 'Made Up'})['executed'] is False


def test_agent_doorks_tools_do_not_expose_sdc_or_execute(monkeypatch, tmp_path):
    import sys
    captured = {}
    class FakeAgent:
        def __init__(self, **kwargs): captured.update(kwargs)
    class FakeRunConfig:
        def __init__(self, **kwargs): pass
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            return SimpleNamespace(final_output='I can prepare a request for approval.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner,
                       RunConfig=FakeRunConfig, function_tool=lambda fn: fn))
    r = req(tmp_path)
    answer = moses_agent.answer(r, 'Find 1126-01', [])
    assert 'approval' in answer
    assert {fn.__name__ for fn in captured['tools']} == {'propose_supplier_bill_for_approval', 'review_supplier_bill_against_po', 'review_supplier_payment_history', 'review_purchase_order_receiving', 'propose_purchase_order_receipt', 'list_workspace_collections', 'search_workspace_records', 'get_workspace_record', 'search_work_orders', 'propose_work_order_status', 'propose_work_order_schedule', 'propose_estimate_to_draft_invoice', 'propose_draft_purchase_order', 'propose_new_doorks_work_order', 'propose_work_order_estimate', 'inspect_product_page', 'propose_catalog_part', 'preview_dispatch_customer_email', 'propose_vendor_po_email', 'propose_customer_estimate_email', 'get_invoice_stripe_payment_status', 'propose_invoice_stripe_checkout', 'propose_customer_invoice_email', 'get_business_briefing', 'get_moses_permissions', 'prepare_moses_action', 'get_moses_action_receipt', 'get_moses_pending_actions'}
    assert not any('execute' in fn.__name__ for fn in captured['tools'])


def test_doorks_agent_disabled_uses_original_chat_path(monkeypatch, tmp_path):
    monkeypatch.delenv('DOORKS_MOSES_DOORKS_AGENT_ENABLED', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    seed(tmp_path)
    monkeypatch.setattr(moses_agent, 'answer', lambda *_: pytest.fail('Agent called despite disabled flag'))
    result = assistant.chat(assistant.Message(message='Hello'), req(tmp_path))
    assert result['workspace'] == 'doorks'


def test_separate_workspace_action_audit(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    monkeypatch.setenv('DOORKS_SDC_MOSES_ACTIONS_ENABLED', 'true')
    path, _ = seed(tmp_path)
    sdc_path = tmp_path / 'business_workspaces' / 'sdc' / 'orders.json'
    sdc_path.parent.mkdir(parents=True)
    sdc_path.write_text(json.dumps([{'id': 'order-a', 'status': 'Open'}]))
    p = moses_actions.propose(req(tmp_path), 'wo-1', 'Scheduled', platform='doorks')
    assert len(json.loads(path.parent.joinpath('moses_action_proposals.json').read_text())) == 1
    assert not sdc_path.parent.joinpath('moses_action_proposals.json').exists()
    assert json.loads(sdc_path.read_text()) == [{'id': 'order-a', 'status': 'Open'}]


def test_doorks_chat_agent_creates_real_approval_request(monkeypatch, tmp_path):
    import sys
    seed(tmp_path)
    monkeypatch.setenv('DOORKS_MOSES_DOORKS_AGENT_ENABLED', 'true')
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    class FakeAgent:
        def __init__(self, **kwargs): self.tools = {fn.__name__: fn for fn in kwargs['tools']}
    class FakeRunConfig:
        def __init__(self, **kwargs): pass
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            records = json.loads(agent.tools['search_work_orders']('1126-01'))
            assert records['matching_count'] == 1
            created = json.loads(agent.tools['propose_work_order_status'](records['examples'][0]['id'], 'Scheduled'))
            assert created['approval_required'] and not created['executed']
            return SimpleNamespace(final_output='I prepared a status change. Please approve it.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner,
                       RunConfig=FakeRunConfig, function_tool=lambda fn: fn))
    r = req(tmp_path)
    result = assistant.chat(assistant.Message(message='Move work order 1126-01 to Scheduled'), r)
    assert result['action_proposals'][0]['kind'] == 'doorks_work_order_status'
    assert result['action_proposals'][0]['new_status'] == 'Scheduled'
    assert json.loads((tmp_path / 'business_workspaces' / 'doorks' / 'work_orders.json').read_text())[0]['status'] == 'Dispatch'


def test_schedule_approval_preserves_other_fields_and_audits(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    p = assistant.propose_work_order_schedule(assistant.MosesWorkOrderScheduleProposal(
        record_id='wo-1', scheduled_date='2026-12-18', scheduled_time='14:30'), r)['proposal']
    assert json.loads(path.read_text()) == original
    queue = assistant.pending_work_order_actions(r)['proposals']
    assert queue[0]['new_schedule'] == {'scheduled_date': '2026-12-18', 'scheduled_time': '14:30'}
    result = assistant.decide_work_order_action(p['id'], assistant.MosesDecision(approve=True), r)
    assert result['confirmed_schedule'] == {'scheduled_date': '2026-12-18', 'scheduled_time': '14:30'}
    changed = json.loads(path.read_text())[0]
    assert changed['status'] == 'Dispatch' and changed['notes'] == 'untouched'
    assert changed['scheduled_date'] == '2026-12-18' and changed['scheduled_time'] == '14:30'
    audit = json.loads((path.parent / 'moses_action_audit.json').read_text())
    assert audit[0]['kind'] == 'doorks_work_order_schedule'
    assert audit[0]['new_schedule'] == result['confirmed_schedule']
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, p['id'], True, 'doorks')
    assert exc.value.status_code == 409


def test_schedule_rejected_invalid_and_stale(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    for date_value, time_value in [('2026-02-30', '12:30'), ('2026-12-01', '25:00'),
                                   ('2026-12-01', '12:30Z'), ('2026-12-01', '1:30')]:
        with pytest.raises(HTTPException) as exc:
            moses_actions.propose_schedule(r, 'wo-1', date_value, time_value)
        assert exc.value.status_code == 422
    assert json.loads(path.read_text()) == original
    p = moses_actions.propose_schedule(r, 'wo-1', '2026-12-01', '10:00')['proposal']
    assert moses_actions.decide(r, p['id'], False, 'doorks')['state'] == 'rejected'
    assert json.loads(path.read_text()) == original
    p = moses_actions.propose_schedule(r, 'wo-1', '2026-12-02', '11:00')['proposal']
    changed = json.loads(path.read_text())
    changed[0]['scheduled_date'] = '2026-12-04'
    path.write_text(json.dumps(changed))
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, p['id'], True, 'doorks')
    assert exc.value.status_code == 409
    assert json.loads(path.read_text())[0]['scheduled_date'] == '2026-12-04'


def test_schedule_blocks_vendor_assignment_before_and_after_proposal(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    assignment_path = path.parent / 'vendor_assignments.json'
    assignment = [{'id': 'vendor-1', 'work_order_number': '1126-01', 'scheduled_date': '2026-12-01'}]
    assignment_path.write_text(json.dumps(assignment))
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_schedule(r, 'wo-1', '2026-12-02', '12:00')
    assert exc.value.status_code == 409
    assignment_path.write_text('[]')
    p = moses_actions.propose_schedule(r, 'wo-1', '2026-12-02', '12:00')['proposal']
    assignment_path.write_text(json.dumps(assignment))
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, p['id'], True, 'doorks')
    assert exc.value.status_code == 409
    assert json.loads(path.read_text()) == original


def test_schedule_blocks_multi_visit_and_requires_role_and_flag(monkeypatch, tmp_path):
    path, original = seed(tmp_path)
    r = req(tmp_path)
    monkeypatch.delenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', raising=False)
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_schedule(r, 'wo-1', '2026-12-02', '12:00')
    assert exc.value.status_code == 503
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_schedule(req(tmp_path, 'sdc'), 'wo-1', '2026-12-02', '12:00')
    assert exc.value.status_code == 403
    changed = json.loads(path.read_text())
    changed[0]['visits'] = [{'date': '2026-12-01'}]
    path.write_text(json.dumps(changed))
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_schedule(r, 'wo-1', '2026-12-02', '12:00')
    assert exc.value.status_code == 409
    assert json.loads(path.read_text())[0]['visits'] == [{'date': '2026-12-01'}]


def test_schedule_chat_tool_is_proposal_only(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, original = seed(tmp_path)
    r = req(tmp_path)
    found = assistant._execute_doorks_tool(r, 'search_work_orders', {'query': '1126-01'})
    assert found['matching_count'] == 1
    result = assistant._execute_doorks_tool(r, 'propose_work_order_schedule', {
        'record_id': found['examples'][0]['id'], 'scheduled_date': '2026-12-10', 'scheduled_time': '09:00'})
    assert result['approval_required'] and not result['executed']
    assert result['proposal']['kind'] == 'doorks_work_order_schedule'
    assert json.loads(path.read_text()) == original


def test_schedule_recovers_interrupted_persisted_write(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    path, _ = seed(tmp_path)
    r = req(tmp_path)
    proposal = moses_actions.propose_schedule(r, 'wo-1', '2026-12-11', '09:30')['proposal']
    original_write = moses_actions._write
    fail_once = {'value': True}
    def crash_after_business_write(file_path, records):
        if file_path.name == 'moses_action_audit.json' and fail_once['value']:
            fail_once['value'] = False
            raise OSError('simulated interruption after schedule saved')
        return original_write(file_path, records)
    monkeypatch.setattr(moses_actions, '_write', crash_after_business_write)
    with pytest.raises(OSError):
        moses_actions.decide(r, proposal['id'], True, 'doorks')
    assert json.loads(path.read_text())[0]['scheduled_date'] == '2026-12-11'
    monkeypatch.setattr(moses_actions, '_write', original_write)
    assert moses_actions.recover(r, 'doorks')['states']['executed'] == 1
    audit = json.loads((path.parent / 'moses_action_audit.json').read_text())
    assert len(audit) == 1 and audit[0]['kind'] == 'doorks_work_order_schedule'
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, proposal['id'], True, 'doorks')
    assert exc.value.status_code == 409


def test_moses_invoice_stripe_tools_are_proposal_and_read_only(monkeypatch, tmp_path):
    import sys
    captured = {}
    class FakeAgent:
        def __init__(self, **kwargs): captured.update(kwargs)
    class FakeRunConfig:
        def __init__(self, **kwargs): pass
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            return SimpleNamespace(final_output='I can prepare a test checkout for approval.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner,
                       RunConfig=FakeRunConfig, function_tool=lambda fn: fn))
    r = req(tmp_path)
    moses_agent.answer(r, 'Check invoice payment', [])
    names = {fn.__name__ for fn in captured['tools']}
    assert 'get_invoice_stripe_payment_status' in names
    assert 'propose_invoice_stripe_checkout' in names
    assert 'approve_invoice_stripe_checkout' not in names
    assert 'execute_invoice_stripe_checkout' not in names
