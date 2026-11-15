"""Rev92: supplier bill approval, recovery and workspace boundaries."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_supplier_bill_actions as actions


def req(tmp_path, platform='doorks', role='office_admin'):
    return SimpleNamespace(session={'active_platform':platform},
        state=SimpleNamespace(auth_user={'id':'admin'}, auth_role=role),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def seed(tmp_path):
    po=tmp_path/'business_workspaces/doorks/purchase_orders.json'
    po.parent.mkdir(parents=True)
    po.write_text(json.dumps([dict(id='po1',po_number='PO-22',quantity=4,
                    total=400,vendor='Vendor A',status='Received')]))
    journal=tmp_path/'po_receiving/doorks/events.json'
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps([dict(id='receipt1',po_id='po1',quantity=4)]))
    return po


def test_disabled_and_platform_role(monkeypatch,tmp_path):
    seed(tmp_path)
    with pytest.raises(HTTPException) as exc:
        actions.propose(req(tmp_path),'PO-22','A101',100)
    assert exc.value.status_code==503
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    for platform,role in [('pds','office_admin'),('sdc','office_admin'),('doorks','tech')]:
        with pytest.raises(HTTPException) as exc:
            actions.propose(req(tmp_path,platform,role),'PO-22','A101',100)
        assert exc.value.status_code==403


def test_approval_creates_one_unpaid_bill_and_blocks_duplicate(monkeypatch,tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    seed(tmp_path); r=req(tmp_path)
    p=actions.propose(r,'PO-22','A101',100,'2026-12-10')['proposal']
    assert p['state']=='pending'
    assert not actions.records(r).exists()
    result=actions.decide(r,p['id'],True)
    assert result['executed'] and result['payment_recorded'] is False
    bills=json.loads(actions.records(r).read_text())
    assert len(bills)==1 and bills[0]['paid']==0 and bills[0]['moses_proposal_id']==p['id']
    with pytest.raises(HTTPException) as err:
        actions.decide(r,p['id'],True)
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:
        actions.propose(r,'PO-22','a101',100)
    assert err.value.status_code==409


def test_rejection_and_amount_guard(monkeypatch,tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    seed(tmp_path); r=req(tmp_path)
    p=actions.propose(r,'PO-22','B202',300)['proposal']
    assert actions.decide(r,p['id'],False)['state']=='rejected'
    assert not actions.records(r).exists()
    for amount in [0,500,-5,float('nan'),1.234]:
        with pytest.raises(HTTPException):
            actions.propose(r,'PO-22','C303',amount)


def test_changed_amount_and_partial_receipt_blocked(monkeypatch,tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    po=seed(tmp_path); r=req(tmp_path)
    p=actions.propose(r,'PO-22','A101',100)['proposal']
    row=json.loads(po.read_text());row[0]['total']=300;po.write_text(json.dumps(row))
    with pytest.raises(HTTPException) as exc:
        actions.decide(r,p['id'],True)
    assert exc.value.status_code==409
    assert not actions.records(r).exists()
    journal=tmp_path/'po_receiving/doorks/events.json'
    journal.write_text(json.dumps([dict(po_id='po1',quantity=2)]))
    with pytest.raises(HTTPException) as exc:
        actions.propose(r,'PO-22','B202',100)
    assert exc.value.status_code==409


def test_uncertain_write_recovered_never_resent(monkeypatch,tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    seed(tmp_path); r=req(tmp_path)
    p=actions.propose(r,'PO-22','A101',100)['proposal']
    rows=actions.proposals(r)
    rows[0]['state']='executing';actions.accounting.write(actions.path(r),rows)
    actions.accounting.write(actions.records(r),[dict(id='saved1',moses_proposal_id=p['id'],
        source_po_id='po1',bill_number='A101',amount=100,paid=0)])
    status=actions.pending(r)
    assert status['count']==0
    assert actions.proposals(r)[0]['state']=='executed'
    assert actions.proposals(r)[0]['bill_id']=='saved1'
    with pytest.raises(HTTPException):
        actions.decide(r,p['id'],True)
    assert len(actions.accounting.read(actions.records(r)))==1


def test_uncertain_no_bill_requires_manual_review(monkeypatch,tmp_path):
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    seed(tmp_path); r=req(tmp_path)
    p=actions.propose(r,'PO-22','A101',100)['proposal']
    rows=actions.proposals(r)
    rows[0]['state']='executing';actions.accounting.write(actions.path(r),rows)
    result=actions.pending(r)
    assert result['proposals'][0]['state']=='needs_review'
    with pytest.raises(HTTPException):
        actions.decide(r,p['id'],True)
