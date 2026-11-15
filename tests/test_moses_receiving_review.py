"""Rev89: receiving reconciliation cannot mutate any workspace journals."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_receiving_review import review


def request(tmp_path, platform='pds', role='office_admin'):
    return SimpleNamespace(session={'active_platform': platform},
        state=SimpleNamespace(auth_user='admin', auth_role=role),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def seed(tmp_path, platform='pds'):
    folder = (tmp_path / 'pds_purchase_orders' if platform == 'pds' else
              tmp_path / 'business_workspaces' / platform)
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / ('records.json' if platform == 'pds' else 'purchase_orders.json')
    p.write_text(json.dumps([{'id':'one','po_number':'PO-00042','quantity':8,
                              'vendor':'Vendor One','status':'Open','internal_notes':'PRIVATE'},
                             {'id':'two','po_number':'PO-00043','quantity':5,'vendor':'Vendor Two'}]))
    journal = tmp_path / 'po_receiving' / platform / 'events.json'
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text(json.dumps([{'po_id':'one','quantity':3,'notes':'SECRET','request_id':'r1'}]))
    return p, journal


@pytest.mark.parametrize('platform', ['pds', 'doorks', 'sdc'])
def test_review_no_writes_and_discrepancy(tmp_path, platform):
    po, journal = seed(tmp_path, platform)
    po_before, journal_before = po.read_bytes(), journal.read_bytes()
    r = request(tmp_path, platform)
    result = review(r, 'PO-00042', 5)
    assert result['workspace'] == platform
    assert (result['ordered_quantity'],result['previously_received'],result['outstanding_quantity']) == (8,3,5)
    assert result['quantity_matches_outstanding'] and not result['receipt_posted']
    assert review(r, 'one', 6)['over_receipt']
    assert review(r, 'one', 2)['short_receipt']
    assert 'PRIVATE' not in str(result) and 'SECRET' not in str(result)
    assert po.read_bytes() == po_before and journal.read_bytes() == journal_before


def test_rejects_missing_stale_invalid_and_unauthorized(tmp_path):
    po, journal = seed(tmp_path)
    for identifier, quantity, status in [('missing',1,404), ('one',-1,409),('one',float('nan'),409)]:
        with pytest.raises(HTTPException) as exc:
            review(request(tmp_path),identifier,quantity)
        assert exc.value.status_code == status
    with pytest.raises(HTTPException) as exc:
        review(request(tmp_path,role='technician'),'one',1)
    assert exc.value.status_code == 403
    po.write_text(json.dumps([{'id':'one','po_number':'PO-00042','quantity':8,'status':'Cancelled'}]))
    with pytest.raises(HTTPException) as exc:
        review(request(tmp_path),'one',1)
    assert exc.value.status_code == 409


def test_overreceived_history_blocked(tmp_path):
    _, journal = seed(tmp_path)
    journal.write_text(json.dumps([{'po_id':'one','quantity':9}]))
    with pytest.raises(HTTPException) as exc:
        review(request(tmp_path),'one',1)
    assert exc.value.status_code == 409
