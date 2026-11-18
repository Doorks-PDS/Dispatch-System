"""Van stock respects inventory authorization, transfers, and optional thresholds."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import pds_van_stock as v
from app.routers import data as d


class _Store:
    def list(self):
        return [{'id': 'tech-1', 'name': 'Test Tech', 'role': 'tech'}]


def _request(tmp_path, *, role='office_admin', platform='pds'):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        data_dir=str(tmp_path), employees_store=_Store(), project_root=str(tmp_path))),
        state=SimpleNamespace(auth_user={'name': 'Office Tester'}, auth_role=role),
        session={'active_platform': platform})


@pytest.fixture
def fixture_data(tmp_path, monkeypatch):
    req = _request(tmp_path)
    monkeypatch.setattr(v, '_parts', lambda request: {'part-a': {'id': 'part-a', 'part_number': 'A-1', 'description': 'Closer', 'min_stock': 2},
                                                       'part-b': {'id': 'part-b', 'part_number': 'B-1', 'description': 'Hinge', 'min_stock': None}})
    monkeypatch.setattr(v, '_people', lambda request: {'tech-1': {'id': 'tech-1', 'name': 'Test Tech', 'role': 'tech'}})
    def balances(request):
        events = d._stock_records(d._pds_stock_path(request))
        totals = {}
        for e in events:
            totals[e['part_id']] = totals.get(e['part_id'], 0) + e['delta']
        for part, delta in v.warehouse_transfer_deltas(request).items():
            totals[part] = totals.get(part, 0) + delta
        return totals
    monkeypatch.setattr(d, '_pds_stock_balances', balances)
    d._write_json_file(d._pds_stock_path(req), [dict(part_id='part-a', delta=10), dict(part_id='part-b', delta=0)])
    return req


def _move(req, movement, qty, rid, part='part-a'):
    return v.movement(v.Movement(employee_id='tech-1', part_id=part, quantity=qty, movement=movement, reason='test record', request_id=rid), req)


def test_template_create_transfer_and_low_alert(fixture_data):
    r = fixture_data
    v.template_item(v.Threshold(part_id='part-a', minimum=3, target=5), r)
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    overview = v.overview(r)
    assert overview['alerts']['vans'] == 1
    assert overview['alerts']['warehouse'] == 0
    result = _move(r, 'load', 4, 'load-key-1')
    assert result['van_quantity'] == 4
    after = v.overview(r)
    assert after['catalog'][0]['warehouse'] == 6
    assert after['alerts']['vans'] == 0
    assert _move(r, 'load', 4, 'load-key-1')['duplicate'] is True
    assert v.overview(r)['catalog'][0]['warehouse'] == 6
    _move(r, 'used', 2, 'usage-key-2')
    assert v.overview(r)['alerts']['vans'] == 1
    _move(r, 'return', 1, 'return-key-3')
    assert v.overview(r)['catalog'][0]['warehouse'] == 7
    assert v.overview(r)['vans'][0]['items'][0]['quantity'] == 1


def test_no_transfer_of_unverified_or_insufficient_stock(fixture_data):
    r = fixture_data
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    with pytest.raises(HTTPException) as exc:
        _move(r, 'load', 11, 'large-load')
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        _move(r, 'return', 2, 'bad-return')
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        _move(r, 'load', 1, 'unknown-part', part='missing')
    assert exc.value.status_code == 404


def test_physical_count_not_warehouse_transfer_and_blank_threshold(fixture_data):
    r=fixture_data
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    _move(r, 'count', 4, 'count-key-1', part='part-b')
    response=v.overview(r)
    assert next(x for x in response['catalog'] if x['id']=='part-b')['warehouse']==0
    assert response['alerts']=={'vans': 0, 'warehouse': 0}
    assert response['vans'][0]['items'][0]['quantity']==4


def test_office_only_writes_and_workspace_isolation(fixture_data):
    req=fixture_data
    tech=_request(req.app.state.data_dir, role='tech')
    with pytest.raises(HTTPException) as exc:
        v.set_up_van(v.VanSetup(employee_id='tech-1'), tech)
    assert exc.value.status_code==403
    other=_request(req.app.state.data_dir, platform='sdc')
    with pytest.raises(HTTPException) as exc:
        v.overview(other)
    assert exc.value.status_code==403


def test_request_id_payload_mismatch_and_van_specific_level(fixture_data):
    r=fixture_data
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    v.van_item('tech-1', v.Threshold(part_id='part-a',minimum=2,target=4), r)
    _move(r,'load',2,'same-key-1')
    with pytest.raises(HTTPException) as exc:
        _move(r,'load',3,'same-key-1')
    assert exc.value.status_code==409
    assert v.overview(r)['vans'][0]['items'][0]['minimum']==2


def test_zero_physical_count_is_allowed(fixture_data):
    r=fixture_data
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    _move(r,'count',3,'first-count')
    _move(r,'count',0,'zero-count')
    assert v.overview(r)['vans'][0]['items'][0]['quantity']==0
    with pytest.raises(HTTPException) as exc:
        _move(r,'load',0,'bad-zero')
    assert exc.value.status_code==422
