"""Combined purchasing lifecycle on temporary records; never touches PDS/SDC production data."""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.services import moses_receiving_actions as receiving
from app.services import moses_supplier_bill_actions as billing
from app.services import moses_supplier_payment_review as payments
from app.routers import pds_purchase_orders as store


def request(tmp, platform='doorks'):
    return SimpleNamespace(
        session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id': 'release-admin'}, auth_role='office_admin'),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp))),
    )


def put_po(tmp, platform='doorks', qty=8, total=400):
    if platform == 'pds':
        path = tmp/'pds_purchase_orders'/'records.json'
    else:
        path = tmp/'business_workspaces'/platform/'purchase_orders.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{'id': 'po-integrated', 'po_number': 'PO-E2E',
                                 'vendor': 'Test Only Vendor', 'quantity': qty,
                                 'total': total, 'status': 'Open'}]))
    return path


def test_doorks_receiving_then_bill_approval_with_no_payment(tmp_path, monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    po_file=put_po(tmp_path)
    original=po_file.read_bytes()
    r=request(tmp_path)
    # One partial receipt does not justify a full supplier bill.
    first=receiving.propose(r,'PO-E2E',3,'SLIP-A')['proposal']
    assert receiving.decide(r,first['id'],True)['executed']
    with pytest.raises(HTTPException) as err:
        billing.propose(r,'PO-E2E','BILL-E2E',400)
    assert err.value.status_code == 409
    second=receiving.propose(r,'PO-E2E',5,'SLIP-B')['proposal']
    assert receiving.decide(r,second['id'],True)['executed']
    assert len(store._receive_events(r,'doorks')) == 2
    assert po_file.read_bytes() == original
    # A proposed bill is not an accounting write.
    candidate=billing.propose(r,'PO-E2E','BILL-E2E',400)['proposal']
    assert not billing.records(r).exists()
    assert billing.decide(r,candidate['id'],True)['executed']
    rows=json.loads(billing.records(r).read_text())
    assert len(rows)==1 and rows[0]['paid']==0
    assert rows[0]['moses_proposal_id']==candidate['id']
    # Repeated approve/duplicate invoice cannot cause a second bill.
    with pytest.raises(HTTPException):
        billing.decide(r,candidate['id'],True)
    with pytest.raises(HTTPException):
        billing.propose(r,'PO-E2E','bill-e2e',400)
    assert len(json.loads(billing.records(r).read_text()))==1
    assert po_file.read_bytes()==original


def test_cross_workspace_receipts_do_not_create_doorks_bill(tmp_path, monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED','true')
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED','true')
    put_po(tmp_path,'sdc')
    r=request(tmp_path,'sdc')
    proposal=receiving.propose(r,'PO-E2E',8,'SDC-TEST-ONLY')['proposal']
    assert receiving.decide(r,proposal['id'],True)['executed']
    assert not (tmp_path/'business_workspaces'/'doorks').exists()
    with pytest.raises(HTTPException) as exc:
        billing.propose(r,'PO-E2E','BILL-SDC',400)
    assert exc.value.status_code==403
    assert not (tmp_path/'business_workspaces'/'doorks').exists()
