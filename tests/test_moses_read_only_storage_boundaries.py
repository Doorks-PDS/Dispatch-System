"""Release regression: business reviews must not create missing data folders."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app.routers import pds_purchase_orders as po_store
from app.services import moses_receiving_review, moses_supplier_bill_review, moses_supplier_payment_review


def request(tmp_path, platform):
    return SimpleNamespace(
        session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id': 'office-test'}, auth_role='office_admin'),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))),
    )


@pytest.mark.parametrize('platform', ['pds', 'doorks', 'sdc'])
def test_missing_receiving_lookup_does_not_create_directories(tmp_path, platform):
    req = request(tmp_path, platform)
    assert po_store._receive_events(req, platform) == []
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(HTTPException) as exc:
        moses_receiving_review.review(req, 'PO-404')
    assert exc.value.status_code == 404
    assert list(tmp_path.iterdir()) == []


def test_missing_supplier_bill_review_does_not_create_accounting_or_receiving(tmp_path):
    req = request(tmp_path, 'doorks')
    with pytest.raises(HTTPException) as exc:
        moses_supplier_bill_review.review(req, 'PO-404', 'INV-404', 20.00)
    assert exc.value.status_code == 404
    assert list(tmp_path.iterdir()) == []


def test_missing_supplier_payment_review_does_not_create_lock(tmp_path):
    req = request(tmp_path, 'doorks')
    with pytest.raises(HTTPException) as exc:
        moses_supplier_payment_review.review(req, 'INV-404')
    assert exc.value.status_code == 404
    assert list(tmp_path.iterdir()) == []


def test_new_receiving_write_still_creates_journal_on_approved_po(tmp_path):
    req = request(tmp_path, 'pds')
    records, _ = po_store._paths(req)
    po_store._write(records, [{'id': 'po-ok', 'po_number': 'PO-1', 'quantity': 5, 'vendor': 'Test'}])
    assert not (tmp_path / 'po_receiving').exists()
    result = po_store.receive_po('pds', 'po-ok', po_store.ReceiveInput(
        quantity=2, reference='SLIP-1', request_id='test-receipt-1'), req)
    assert result['outstanding'] == 3
    assert (tmp_path / 'po_receiving' / 'pds' / 'events.json').is_file()
    assert len(po_store._receive_events(req, 'pds')) == 1
