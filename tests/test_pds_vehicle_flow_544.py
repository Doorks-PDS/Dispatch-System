"""5.44 regression: service history persists, stays office-only and does not post accounting entries."""
from fastapi import HTTPException
import pytest
from app.routers import pds_van_stock as van
from test_pds_van_stock import fixture_data


def test_vehicle_service_and_incident_history_persists_with_actor(fixture_data):
    request = fixture_data
    van.set_up_van(van.VanSetup(employee_id='tech-1'), request)
    van.save_vehicle('tech-1', van.VehicleDetails(make='Ford', next_service='2026-11-18'), request)
    event = van.VehicleServiceEvent(kind='service', date='2026-11-18', odometer='60321', provider='Fleet Shop', notes='Changed oil and filters', request_id='record-1')
    saved = van.record_vehicle_service('tech-1', event, request)
    assert saved['ok'] is True
    assert saved['event']['kind'] == 'service'
    assert saved['event']['created_by']
    assert van.record_vehicle_service('tech-1', event, request)['reused'] is True
    with pytest.raises(HTTPException) as reused_id:
        van.record_vehicle_service('tech-1', van.VehicleServiceEvent(kind='service',date='2026-11-18', notes='Different details', request_id='record-1'),request)
    assert reused_id.value.status_code == 409
    van.record_vehicle_service('tech-1', van.VehicleServiceEvent(kind='accident', date='2026-11-18', notes='Rear bumper incident documented'), request)
    item=van.overview(request)['vans'][0]
    assert item['vehicle']['next_service']=='2026-11-18'
    assert [x['kind'] for x in item['service_events']] == ['accident', 'service']
    assert len(van._read(van._path(request))['vans']['tech-1']['service_events']) == 2
    assert not any(k in saved for k in ['expense','tax','payment'])


def test_vehicle_history_denies_technician_writes_and_sensitive_read(fixture_data):
    r=fixture_data
    van.set_up_van(van.VanSetup(employee_id='tech-1'), r)
    event=van.VehicleServiceEvent(kind='repair', date='2026-11-18', notes='Repaired tail light')
    r.state.auth_role='tech'
    assert van.overview(r)['vans'][0]['service_events']==[]
    with pytest.raises(HTTPException) as denied:
        van.record_vehicle_service('tech-1',event,r)
    assert denied.value.status_code==403
    r.state.auth_role='office_admin'
    with pytest.raises(HTTPException) as missing:
        van.record_vehicle_service('missing',event,r)
    assert missing.value.status_code==404
    with pytest.raises(HTTPException) as invalid:
        van.record_vehicle_service('tech-1',van.VehicleServiceEvent(kind='repair',date='2026-99-99',notes='Bad date'),r)
    assert invalid.value.status_code==422


def test_vehicle_flow_ui_search_retries_and_inventory_table_exist():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'static/app.js').read_text()
    for anchor in ('cf_existing_door_search','cf_existing_door_results','Search door ID, location',
                   'Send to (saved customer email)', 'Discarded · Not sent', '760) 233-5037', 'reception@prioritydoors.com',
                   'Fleet Hub', 'Fleet Info/Stock', 'Vehicle Info', 'service-events',
                   'Search part #, manufacturer, description or supplier', 'Low stock only',
                   'Stock Movement History', 'Show next '):
        assert anchor in source,anchor
