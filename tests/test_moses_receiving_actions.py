"""Rev90 — approval-only receiving through original journal, not duplicate inventory."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services import moses_receiving_actions as actions
from app.routers import pds_purchase_orders as store


def req(tmp_path, platform='pds', role='office_admin'):
    return SimpleNamespace(session={'active_platform': platform},
        state=SimpleNamespace(auth_user='office-1', auth_role=role),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def seed(tmp_path, platform):
    folder = tmp_path / ('pds_purchase_orders' if platform == 'pds' else 'business_workspaces/'+platform)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('records.json' if platform == 'pds' else 'purchase_orders.json')
    path.write_text(json.dumps([{'id':'po-1','po_number':'PO-001','vendor':'Sample Vendor',
                                 'quantity':8,'status':'Open'}]))
    return path


@pytest.mark.parametrize('platform', ['pds','doorks','sdc'])
def test_approve_posts_once_and_preserves_original_po(tmp_path, monkeypatch, platform):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    original = seed(tmp_path, platform)
    content = original.read_bytes()
    r = req(tmp_path, platform)
    result = actions.propose(r,'PO-001',3,'SLIP-123')
    assert result['approval_required'] and not result['executed']
    assert not store._receive_events(r,platform)
    approval = actions.decide(r,result['proposal']['id'],True)
    assert approval['executed'] and approval['outstanding'] == 5
    assert approval['inventory_changed'] is False and approval['supplier_bill_created'] is False
    assert original.read_bytes() == content
    events = store._receive_events(r,platform)
    assert len(events) == 1 and events[0]['quantity'] == 3
    assert events[0]['request_id'].endswith(result['proposal']['id'])
    assert not events[0]['to_inventory']
    with pytest.raises(HTTPException) as err:
        actions.decide(r,result['proposal']['id'],True)
    assert err.value.status_code == 409
    assert len(store._receive_events(r,platform)) == 1


def test_rejected_never_posts_and_missing_slip_rejected(tmp_path,monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    seed(tmp_path,'pds'); r=req(tmp_path)
    with pytest.raises(HTTPException):
        actions.propose(r,'PO-001',1,'')
    p=actions.propose(r,'PO-001',2,'SLIP-2')['proposal']
    assert actions.decide(r,p['id'],False)['state']=='rejected'
    assert store._receive_events(r,'pds') == []


def test_stale_quantity_blocks_approval(tmp_path,monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    seed(tmp_path,'pds');r=req(tmp_path)
    p=actions.propose(r,'PO-001',5,'SLIP-3')['proposal']
    store.receive_po('pds','po-1',store.ReceiveInput(quantity=1,reference='other',request_id='outside-1'),r)
    with pytest.raises(HTTPException) as err:
        actions.decide(r,p['id'],True)
    assert err.value.status_code==409
    assert len(store._receive_events(r,'pds'))==1


def test_incomplete_write_recovers_without_duplicate(tmp_path,monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    seed(tmp_path,'pds');r=req(tmp_path)
    p=actions.propose(r,'PO-001',4,'SLIP-4')['proposal']
    original=store.receive_po
    def interrupted(*args, **kwargs):
        original(*args,**kwargs)
        raise RuntimeError('connection lost after committed receipt')
    monkeypatch.setattr(store,'receive_po',interrupted)
    with pytest.raises(RuntimeError):actions.decide(r,p['id'],True)
    assert len(store._receive_events(r,'pds'))==1
    assert actions.pending(r)['count']==0
    with pytest.raises(HTTPException):actions.decide(r,p['id'],True)
    assert len(store._receive_events(r,'pds'))==1


def test_permissions_and_feature_flag(tmp_path,monkeypatch):
    seed(tmp_path,'doorks')
    monkeypatch.delenv('MOSES_RECEIVING_ACTIONS_ENABLED',raising=False)
    with pytest.raises(HTTPException) as err:actions.propose(req(tmp_path,'doorks'),'PO-001',2,'x')
    assert err.value.status_code==503
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    with pytest.raises(HTTPException) as err:actions.propose(req(tmp_path,'doorks','technician'),'PO-001',2,'x')
    assert err.value.status_code==403


def test_duplicate_slip_and_overreceipt(tmp_path,monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    seed(tmp_path,'sdc');r=req(tmp_path,'sdc')
    with pytest.raises(HTTPException) as err:actions.propose(r,'PO-001',9,'SLIP-9')
    assert err.value.status_code==409
    p=actions.propose(r,'PO-001',2,'SLIP-9')['proposal']
    with pytest.raises(HTTPException):actions.propose(r,'PO-001',2,'SLIP-9')
    actions.decide(r,p['id'],True)
    with pytest.raises(HTTPException) as err:actions.propose(r,'PO-001',1,'SLIP-9')
    assert err.value.status_code==409 or err.value.status_code==422


def test_pending_reference_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED', 'true')
    seed(tmp_path, 'pds'); r = req(tmp_path)
    actions.propose(r, 'PO-001', 2, 'Slip-101')
    with pytest.raises(HTTPException) as err:
        actions.propose(r, 'PO-001', 2, '  SLIP-101  ')
    assert err.value.status_code == 409
    assert len(actions.pending(r)['proposals']) == 1
