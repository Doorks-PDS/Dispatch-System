"""Real Doorks work-order creation via approval; no PDS calendar writes."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_actions
from app.routers import doorks_assistant
from app.routers.workspaces import create, Record


def request(tmp_path, platform='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'admin'}, auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path):
    base = tmp_path / 'business_workspaces' / 'doorks'
    base.mkdir(parents=True, exist_ok=True)
    (base / 'customers.json').write_text(json.dumps([{'id': 'cust-1', 'name': 'Acme Doors', 'active': True}]))
    return base


def test_propose_create_and_prevent_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path)
    r = request(tmp_path)
    response = doorks_assistant._execute_work_order_tool(r, 'cust-1', 'Inspect loading door', 'Main Entrance')
    assert response['approval_required'] and not response['executed']
    assert not (base / 'work_orders.json').exists()
    proposal_id = response['proposal']['id']
    approved = moses_actions.decide(r, proposal_id, True, 'doorks')
    assert approved['executed'] and approved['confirmed_status'] == 'Dispatch'
    assert approved['job_number'].endswith('-01')
    records = json.loads((base / 'work_orders.json').read_text())
    assert len(records) == 1
    assert records[0]['customer'] == 'Acme Doors'
    assert records[0]['source_moses_proposal_id'] == proposal_id
    assert records[0]['job_number'] == approved['job_number']
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, proposal_id, True, 'doorks')
    assert exc.value.status_code == 409
    assert len(json.loads((base / 'work_orders.json').read_text())) == 1


def test_reject_stale_customer_and_roles(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path)
    r = request(tmp_path)
    with pytest.raises(HTTPException):
        moses_actions.propose_work_order(r, 'made-up', 'Inspect')
    with pytest.raises(HTTPException):
        moses_actions.propose_work_order(r, 'cust-1', '')
    rejected = moses_actions.propose_work_order(r, 'cust-1', 'Inspect')['proposal']
    assert moses_actions.decide(r, rejected['id'], False, 'doorks')['state'] == 'rejected'
    proposal = moses_actions.propose_work_order(r, 'cust-1', 'Inspect')['proposal']
    customers = base / 'customers.json'
    customers.write_text(json.dumps([{'id': 'cust-1', 'name': 'Acme Doors NEW', 'active': True}]))
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, proposal['id'], True, 'doorks')
    assert exc.value.status_code == 409
    assert not (base / 'work_orders.json').exists()
    for req in [request(tmp_path, platform='pds'), request(tmp_path, role='technician')]:
        with pytest.raises(HTTPException):
            moses_actions.propose_work_order(req, 'cust-1', 'Inspect')


def test_recover_after_write_before_completion(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path)
    r = request(tmp_path)
    proposal = moses_actions.propose_work_order(r, 'cust-1', 'Inspect')['proposal']
    proposals = base / 'moses_action_proposals.json'
    records = json.loads(proposals.read_text())
    records[0]['state'] = 'executing'
    proposals.write_text(json.dumps(records))
    create('doorks', 'work_orders', Record(data={**proposal['details'], 'source_moses_proposal_id': proposal['id']}), r)
    recovered = moses_actions.recover(r, 'doorks')
    assert recovered['states']['executed'] == 1
    assert len(json.loads((base / 'work_orders.json').read_text())) == 1
    with pytest.raises(HTTPException):
        moses_actions.decide(r, proposal['id'], True, 'doorks')
    assert len(json.loads((base / 'moses_action_audit.json').read_text())) == 1


def test_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', raising=False)
    seed(tmp_path)
    with pytest.raises(HTTPException) as exc:
        moses_actions.propose_work_order(request(tmp_path), 'cust-1', 'Inspect')
    assert exc.value.status_code == 503
