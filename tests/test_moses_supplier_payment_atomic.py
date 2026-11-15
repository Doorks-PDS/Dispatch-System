"""Rev97 manual supplier payment record is atomic, idempotent and recoverable.
These tests never initiate or verify an external bank transfer.
"""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import doorks_workflow as wf, doorks_accounting as ac


def request(tmp):
    return SimpleNamespace(session={'active_platform':'doorks'},
        state=SimpleNamespace(auth_user={'name':'Office'}, auth_role='office_admin'),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp))))


def seed(req, *, paid=0, events=None):
    folder=ac.base(req)
    ac.write(folder/'supplier_bills.json', [dict(id='b1', bill_number='INV-1', amount=100,
                                                paid=paid,status='Open')])
    ac.write(folder/'workflow_events.json', events if events is not None else [])
    return folder


def load(folder, name):
    return ac.read(folder/name)


def test_payment_and_repeat_reference_are_idempotent(tmp_path):
    req=request(tmp_path); folder=seed(req)
    first=wf.supplier_payment('b1',wf.Money(amount=40,reference='WIRE-123'),req)
    assert first['item']['paid']==40 and not first['already_exists']
    again=wf.supplier_payment('b1',wf.Money(amount=40,reference='wire-123'),req)
    assert again['already_exists'] and again['item']['paid']==40
    assert len(load(folder,'workflow_events.json'))==1
    assert len(load(folder,'supplier_bills.json')[0]['moses_payment_entries'])==1


def test_different_payment_on_same_reference_is_rejected(tmp_path):
    req=request(tmp_path); seed(req)
    wf.supplier_payment('b1',wf.Money(amount=40,reference='ACH-1'),req)
    with pytest.raises(HTTPException) as ex:
        wf.supplier_payment('b1',wf.Money(amount=41,reference='ACH-1'),req)
    assert ex.value.status_code==409


def test_interrupted_event_mirror_can_be_recovered_once(tmp_path,monkeypatch):
    req=request(tmp_path); folder=seed(req)
    original=wf._append_payment_mirror
    def interrupted(*args,**kwargs):
        raise OSError('simulated failure after atomic bill commit')
    monkeypatch.setattr(wf,'_append_payment_mirror',interrupted)
    with pytest.raises(OSError):
        wf.supplier_payment('b1',wf.Money(amount=40,reference='ACH-77'),req)
    assert load(folder,'supplier_bills.json')[0]['paid']==40
    assert load(folder,'workflow_events.json')==[]
    monkeypatch.setattr(wf,'_append_payment_mirror',original)
    with pytest.raises(HTTPException) as ex:
        wf.supplier_payment('b1',wf.Money(amount=10,reference='ACH-78'),req)
    assert ex.value.status_code==409
    recovered=wf.supplier_payment('b1',wf.Money(amount=40,reference='ach-77'),req)
    assert recovered['already_exists'] and recovered['item']['paid']==40
    assert len(load(folder,'workflow_events.json'))==1


def test_inconsistent_historical_ledger_blocks_new_payment(tmp_path):
    req=request(tmp_path); folder=seed(req,paid=50,events=[])
    with pytest.raises(HTTPException) as ex:
        wf.supplier_payment('b1',wf.Money(amount=10,reference='WIRE-1'),req)
    assert ex.value.status_code==409
    assert load(folder,'supplier_bills.json')[0]['paid']==50


def test_ref_required_and_amount_bounded(tmp_path):
    req=request(tmp_path); seed(req)
    for amount,ref in [(20,''),(101,'ACH-X'),(20,' '*3)]:
        with pytest.raises(HTTPException):
            wf.supplier_payment('b1',wf.Money(amount=amount,reference=ref),req)
