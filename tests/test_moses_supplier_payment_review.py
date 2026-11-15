"""Rev96 supplier payment consistency: no payments, writes, or cross-workspace access."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_supplier_payment_review import review


def request(tmp, platform='doorks', role='office_admin'):
    return SimpleNamespace(session={'active_platform':platform}, state=SimpleNamespace(
        auth_user={'id':'staff'}, auth_role=role), app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp))))


def seed(tmp, paid=50, events=None):
    root=tmp/'business_workspaces'/'doorks'/'accounting'
    root.mkdir(parents=True,exist_ok=True)
    bills=root/'supplier_bills.json'
    history=root/'workflow_events.json'
    bills.write_text(json.dumps([{'id':'bill-1','bill_number':'ABC-101','vendor':'Real Supplier',
        'amount':100,'paid':paid, 'status':'Partially Paid', 'secret_note':'private'}]))
    if events is None:
        events=[{'id':'pay-1','kind':'supplier_bill','source_id':'bill-1','action':'payment_sent',
                 'amount':50,'reference':'check-123','private_note':'private'},
                {'id':'ignore','kind':'receivable','source_id':'bill-1','action':'payment_sent','amount':999}]
    history.write_text(json.dumps(events))
    return bills,history


def test_agreeing_events_is_still_not_bank_verified(tmp_path):
    paths=seed(tmp_path)
    before=[f.read_bytes() for f in paths]
    r=review(request(tmp_path),'abc-101')
    assert r['recorded_paid']=='50.00' and r['payment_event_total']=='50.00'
    assert r['remaining_balance']=='50.00' and not r['issues']
    assert not r['external_payment_verified'] and not r['payment_executed']
    assert 'private' not in str(r)
    assert before==[f.read_bytes() for f in paths]


def test_interrupted_or_missing_payment_event_is_flagged(tmp_path):
    seed(tmp_path,paid=0)
    r=review(request(tmp_path),'bill-1')
    assert r['requires_manual_review'] and 'differ' in str(r['issues'])
    seed(tmp_path,paid=50,events=[])
    r=review(request(tmp_path),'bill-1')
    assert r['requires_manual_review']


def test_repeated_references_or_overpaid(tmp_path):
    seed(tmp_path,paid=110,events=[
        {'id':'a','kind':'supplier_bill','source_id':'bill-1','action':'payment_sent','amount':50,'reference':'WIRE1'},
        {'id':'b','kind':'supplier_bill','source_id':'bill-1','action':'payment_sent','amount':60,'reference':'wire1'}])
    r=review(request(tmp_path),'bill-1')
    assert r['requires_manual_review']
    assert 'exceeds' in str(r['issues']) and 'Repeated' in str(r['issues'])


def test_ambiguous_bill_and_bad_amount(tmp_path):
    bills,_=seed(tmp_path)
    data=json.loads(bills.read_text()); data.append({'id':'bill-2','bill_number':'abc-101','amount':100,'paid':0})
    bills.write_text(json.dumps(data))
    with pytest.raises(HTTPException) as e: review(request(tmp_path),'abc-101')
    assert e.value.status_code==409
    data[0]['amount']=float('nan'); bills.write_text(json.dumps(data))
    with pytest.raises(HTTPException): review(request(tmp_path),'bill-1')


def test_platform_roles_and_not_found(tmp_path):
    seed(tmp_path)
    for platform,role in [('pds','office_admin'),('sdc','office_admin'),('doorks','technician')]:
        with pytest.raises(HTTPException) as e: review(request(tmp_path,platform,role),'bill-1')
        assert e.value.status_code==403
    with pytest.raises(HTTPException) as e: review(request(tmp_path),'missing')
    assert e.value.status_code==404
