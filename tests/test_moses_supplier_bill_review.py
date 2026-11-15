"""Rev91: read-only supplier bill/PO matching, with no cross-workspace writes."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_supplier_bill_review import review


def request(tmp_path, platform='doorks', role='office_admin'):
    return SimpleNamespace(session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id':'admin'}, auth_role=role),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def seed(tmp_path):
    po = tmp_path / 'business_workspaces' / 'doorks' / 'purchase_orders.json'
    po.parent.mkdir(parents=True)
    po.write_text(json.dumps([{'id':'one','po_number':'PO-00042','quantity':8, 'total':800,
                              'vendor':'Supplier A','status':'Open','private_note':'dont expose'}]))
    journal = tmp_path / 'po_receiving' / 'doorks' / 'events.json'
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps([{'po_id':'one','quantity':3,'notes':'private'}]))
    bills = tmp_path / 'business_workspaces' / 'doorks' / 'accounting' / 'supplier_bills.json'
    bills.parent.mkdir(parents=True)
    bills.write_text(json.dumps([{'source_po_id':'one','bill_number':'INV-101', 'amount':300,'paid':100,
                                  'internal_note':'hide me'},
                                 {'source_po_id':'another','bill_number':'INV-101','amount':123}]))
    return po,journal,bills


def test_matches_and_never_writes(tmp_path):
    paths = seed(tmp_path)
    before = [p.read_bytes() for p in paths]
    result=review(request(tmp_path),'PO-00042','inv-101',400)
    assert result['bill_already_exists'] and result['existing_bill_count'] == 1
    assert result['existing_billed_amount']==300 and result['po_total']==800
    assert result['received_quantity']==3 and result['outstanding_quantity']==5
    assert result['bill_created'] is False and result['payment_recorded'] is False
    assert 'hide me' not in str(result) and 'dont expose' not in str(result)
    assert before == [p.read_bytes() for p in paths]


def test_overamount_partial_and_missing_po_total(tmp_path):
    po,_,_ = seed(tmp_path)
    r=review(request(tmp_path),'one','NEW-102',600)
    assert any('exceeds PO total' in issue for issue in r['issues'])
    rows=json.loads(po.read_text());rows[0].pop('total');rows[0]['unit_cost']=100
    po.write_text(json.dumps(rows))
    r=review(request(tmp_path),'one','NEW-102',200)
    assert r['po_total'] is None and r['po_subtotal_only']==800
    assert any('not established' in issue for issue in r['issues'])


def test_rejects_invalid_amounts_and_wrong_roles(tmp_path):
    seed(tmp_path)
    for amount in (float('nan'), float('inf'), -1, 1.234, True):
        with pytest.raises(HTTPException):
            review(request(tmp_path),'one','B123',amount)
    for platform,role in [('pds','office_admin'),('sdc','office_admin'),('doorks','technician')]:
        with pytest.raises(HTTPException) as e:
            review(request(tmp_path,platform,role),'one','B123',10)
        assert e.value.status_code==403


def test_duplicate_bill_numbers(tmp_path):
    *_, bills=seed(tmp_path)
    data=json.loads(bills.read_text());data.append({'source_po_id':'one','bill_number':'inv-101','amount':10})
    bills.write_text(json.dumps(data))
    r=review(request(tmp_path),'one','',10)
    assert r['existing_bill_count']==2
    assert any('Duplicate' in issue for issue in r['issues'])
