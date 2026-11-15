"""Verified work-order to unissued, unpriced draft estimate workflow."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_actions
from app.routers import doorks_assistant


def req(root, platform='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'admin'}, auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=root)))


def seed(root):
    base = root / 'business_workspaces' / 'doorks'
    base.mkdir(parents=True, exist_ok=True)
    (base / 'customers.json').write_text(json.dumps([{'id': 'cust1', 'name': 'Acme', 'active': True}]))
    (base / 'work_orders.json').write_text(json.dumps([{'id': 'job1', 'customer_id': 'cust1',
        'customer': 'Acme', 'job_number': '1126-01', 'address': '10 Test St',
        'description': 'Replace damaged hinges', 'status': 'To Be Quoted'}]))
    return base


def test_draft_requires_approval_and_no_invented_prices(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path); r = req(tmp_path)
    result = doorks_assistant._execute_work_order_estimate_tool(r, 'job1', 'Check closer too')
    assert result['approval_required'] and result['executed'] is False
    assert not (base / 'estimates_invoices.json').exists()
    proposal_id = result['proposal']['id']
    response = moses_actions.decide(r, proposal_id, True, 'doorks')
    assert response['executed'] and response['pricing_required'] and response['number_required']
    docs = json.loads((base / 'estimates_invoices.json').read_text())
    assert len(docs) == 1
    doc = docs[0]
    assert doc['source_work_order_id'] == 'job1' and doc['document_type'] == 'Estimate'
    assert doc['document_number'] == '' and doc['status'] == 'Draft'
    assert doc['amount'] == 0 and doc['line_items'] == '[]'
    assert doc['description'] == 'Replace damaged hinges'
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, proposal_id, True, 'doorks')
    assert exc.value.status_code == 409
    assert len(json.loads((base / 'estimates_invoices.json').read_text())) == 1


def test_reject_missing_stale_and_wrong_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path); r = req(tmp_path)
    with pytest.raises(HTTPException):
        moses_actions.propose_work_order_estimate(r, 'fake')
    with pytest.raises(HTTPException):
        moses_actions.propose_work_order_estimate(req(tmp_path, 'sdc'), 'job1')
    rejected = moses_actions.propose_work_order_estimate(r, 'job1')['proposal']
    assert moses_actions.decide(r, rejected['id'], False, 'doorks')['state'] == 'rejected'
    proposal = moses_actions.propose_work_order_estimate(r, 'job1')['proposal']
    (base / 'work_orders.json').write_text(json.dumps([{'id': 'job1', 'customer_id': 'cust1',
        'customer': 'Acme', 'job_number': '1126-01', 'description': 'New scope'}]))
    with pytest.raises(HTTPException) as exc:
        moses_actions.decide(r, proposal['id'], True, 'doorks')
    assert exc.value.status_code == 409
    assert not (base / 'estimates_invoices.json').exists()


def test_recovery_after_document_write(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path); r = req(tmp_path)
    proposal = moses_actions.propose_work_order_estimate(r, 'job1')['proposal']
    props = base / 'moses_action_proposals.json'
    rows = json.loads(props.read_text()); rows[0]['state'] = 'executing'
    props.write_text(json.dumps(rows))
    (base / 'estimates_invoices.json').write_text(json.dumps([{'id': 'est1',
        'source_moses_proposal_id': proposal['id'], 'document_type': 'Estimate',
        'status': 'Draft', 'source_work_order_id': 'job1'}]))
    assert moses_actions.recover(r, 'doorks')['states']['executed'] == 1
    assert len(json.loads((base / 'moses_action_audit.json').read_text())) == 1
    with pytest.raises(HTTPException):
        moses_actions.decide(r, proposal['id'], True, 'doorks')


def test_recovery_before_document_write(tmp_path, monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED', 'true')
    base = seed(tmp_path); r = req(tmp_path)
    proposal = moses_actions.propose_work_order_estimate(r, 'job1')['proposal']
    props = base / 'moses_action_proposals.json'
    rows = json.loads(props.read_text()); rows[0]['state'] = 'executing'
    props.write_text(json.dumps(rows))
    assert moses_actions.recover(r, 'doorks')['states']['pending'] == 1
    assert moses_actions.decide(r, proposal['id'], True, 'doorks')['executed']
