"""Consolidated release tests of the *real* purchasing/receiving/bill services.

These tests use temporary data only; they do not pay vendors or connect providers.
Doorks historic test POs are deliberately not migrated or modified.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import moses_receiving_actions as receiving
from app.services import moses_supplier_bill_actions as bills
from app.services import moses_supplier_bill_review as bill_review
from app.services import moses_supplier_payment_review as payment_review
from app.routers import pds_purchase_orders as po_store


def req(root, platform='doorks'):
    return SimpleNamespace(
        session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id': 'test-office'}, auth_role='office_admin'),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(root)))
    )


def seed(root, platform, po_id='po-new', qty=8, total=800):
    folder = root / ('pds_purchase_orders' if platform == 'pds' else f'business_workspaces/{platform}')
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ('records.json' if platform == 'pds' else 'purchase_orders.json')
    target.write_text(json.dumps([{
        'id': po_id, 'po_number': 'PO-NEW', 'vendor': 'Vendor Test',
        'quantity': qty, 'total': total, 'status': 'Open',
    }]))
    return target


def enable(monkeypatch):
    monkeypatch.setenv('MOSES_RECEIVING_ACTIONS_ENABLED', 'true')
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED', 'true')


def test_two_receipts_then_supplier_bill_approved_without_payment(tmp_path, monkeypatch):
    enable(monkeypatch)
    record_path = seed(tmp_path, 'doorks')
    original = record_path.read_bytes()
    r = req(tmp_path)
    first = receiving.propose(r, 'PO-NEW', 3, 'SLIP-A')['proposal']
    assert receiving.decide(r, first['id'], True)['outstanding'] == 5
    # Partial receipt cannot justify a full supplier bill, even if proposed.
    with pytest.raises(HTTPException) as error:
        bills.propose(r, 'PO-NEW', 'BILL-01', 800)
    assert error.value.status_code == 409
    second = receiving.propose(r, 'PO-NEW', 5, 'SLIP-B')['proposal']
    assert receiving.decide(r, second['id'], True)['outstanding'] == 0
    verified = bill_review.review(r, 'PO-NEW', 'BILL-01', 800)
    assert verified['received_quantity'] == 8
    assert verified['outstanding_quantity'] == 0
    proposal = bills.propose(r, 'PO-NEW', 'BILL-01', 800)['proposal']
    assert not bills.records(r).exists()
    result = bills.decide(r, proposal['id'], True)
    assert result['executed'] is True and result['payment_recorded'] is False
    recorded = bills.accounting.read(bills.records(r))
    assert len(recorded) == 1
    assert recorded[0]['status'] == 'Open' and recorded[0]['paid'] == 0
    assert recorded[0]['moses_proposal_id'] == proposal['id']
    assert record_path.read_bytes() == original  # no PO quantity rewrite
    assert len(po_store._receive_events(r, 'doorks')) == 2
    assert payment_review.review(r, recorded[0]['id'])['recorded_paid'] == '0.00'


def test_duplicate_receipts_and_bills_do_not_post_again(tmp_path, monkeypatch):
    enable(monkeypatch)
    seed(tmp_path, 'doorks')
    r = req(tmp_path)
    for amount, ref in [(3, 'S1'), (5, 'S2')]:
        p = receiving.propose(r, 'PO-NEW', amount, ref)['proposal']
        receiving.decide(r, p['id'], True)
    bill = bills.propose(r, 'PO-NEW', 'DUPLICATE', 150)['proposal']
    bills.decide(r, bill['id'], True)
    with pytest.raises(HTTPException) as err:
        bills.decide(r, bill['id'], True)
    assert err.value.status_code == 409
    with pytest.raises(HTTPException) as err:
        bills.propose(r, 'PO-NEW', 'duplicate', 150)
    assert err.value.status_code == 409
    assert len(bills.accounting.read(bills.records(r))) == 1
    assert len(po_store._receive_events(r, 'doorks')) == 2


def test_pds_and_sdc_receiving_cannot_be_billed_in_doorks(tmp_path, monkeypatch):
    enable(monkeypatch)
    for platform in ('pds', 'sdc'):
        seed(tmp_path, platform, po_id=f'{platform}-po')
        r = req(tmp_path, platform)
        proposal = receiving.propose(r, 'PO-NEW', 8, f'{platform.upper()}-SLIP')['proposal']
        assert receiving.decide(r, proposal['id'], True)['outstanding'] == 0
        with pytest.raises(HTTPException) as err:
            bills.propose(r, 'PO-NEW', 'NOT-PERMITTED', 800)
        assert err.value.status_code == 403
    assert not (tmp_path / 'business_workspaces/doorks/accounting').exists()
    assert not (tmp_path / 'po_receiving/doorks').exists()


def test_rejecting_second_receipt_keeps_po_open_and_bill_blocked(tmp_path, monkeypatch):
    enable(monkeypatch)
    seed(tmp_path, 'doorks')
    r = req(tmp_path)
    p = receiving.propose(r, 'PO-NEW', 8, 'S-REJECT')['proposal']
    assert receiving.decide(r, p['id'], False)['executed'] is False
    assert po_store._receive_events(r, 'doorks') == []
    with pytest.raises(HTTPException) as err:
        bills.propose(r, 'PO-NEW', 'NO-RECEIPT', 100)
    assert err.value.status_code == 409
    assert not bills.records(r).exists()
