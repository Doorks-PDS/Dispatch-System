"""Rev95: never combine legacy Doorks PO receipt field with journal silently."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import pds_purchase_orders as store, doorks_workflow as workflow
from app.services.moses_receiving_review import review


def req(tmp_path):
    return SimpleNamespace(session={'active_platform': 'doorks'},
        state=SimpleNamespace(auth_user='admin', auth_role='office_admin'),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def seed(tmp_path, legacy=0, journal=()):
    po = tmp_path / 'business_workspaces' / 'doorks' / 'purchase_orders.json'
    po.parent.mkdir(parents=True, exist_ok=True)
    po.write_text(json.dumps([{'id': 'po1', 'po_number':'PO-42', 'quantity': 8,
                               'received_quantity': legacy, 'status':'Open'}]))
    j = tmp_path / 'po_receiving' / 'doorks' / 'events.json'
    j.parent.mkdir(parents=True, exist_ok=True)
    j.write_text(json.dumps([{'po_id':'po1', 'quantity':q, 'request_id':f'id-{n}'}
                             for n,q in enumerate(journal)]))
    return po, j


def post_journal(request, request_id='new'):
    return store.receive_po('doorks', 'po1', store.ReceiveInput(
        quantity=1, reference='packing', request_id=request_id), request)


def post_legacy(request, monkeypatch):
    monkeypatch.setattr(workflow, 'guard', lambda request: None)
    return workflow.receive('po1', workflow.Receiving(quantity=1, reference='packing'), request)


def test_legacy_quantity_blocks_journal_and_ai(tmp_path):
    po,j = seed(tmp_path, legacy=3)
    r=req(tmp_path)
    old=(po.read_bytes(),j.read_bytes())
    with pytest.raises(HTTPException) as err: post_journal(r)
    assert err.value.status_code == 409
    with pytest.raises(HTTPException) as err: review(r, 'PO-42', 1)
    assert err.value.status_code == 409
    assert (po.read_bytes(),j.read_bytes()) == old


def test_journal_receipt_blocks_legacy_endpoint(tmp_path, monkeypatch):
    po,j = seed(tmp_path, journal=[2])
    r=req(tmp_path)
    old=(po.read_bytes(),j.read_bytes())
    with pytest.raises(HTTPException) as err: post_legacy(r, monkeypatch)
    assert err.value.status_code == 409
    assert (po.read_bytes(),j.read_bytes()) == old


def test_unmixed_receiving_paths_still_work(tmp_path, monkeypatch):
    po,j=seed(tmp_path)
    r=req(tmp_path)
    assert post_journal(r)['received'] == 1
    with pytest.raises(HTTPException): post_legacy(r,monkeypatch)
    # A separate PO without journal receipts remains writable by the old UI.
    po,j=seed(tmp_path)
    assert post_legacy(r,monkeypatch)['item']['received_quantity'] == 1
    with pytest.raises(HTTPException): post_journal(r)


def test_existing_request_id_retry_survives_legacy_state_change(tmp_path):
    po,j=seed(tmp_path,journal=[2])
    r=req(tmp_path)
    data=json.loads(po.read_text());data[0]['received_quantity']=2
    po.write_text(json.dumps(data))
    assert post_journal(r, request_id='id-0')['duplicate'] is True
    with pytest.raises(HTTPException): post_journal(r, request_id='another')
