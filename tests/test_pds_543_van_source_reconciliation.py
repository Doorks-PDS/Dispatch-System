"""PDS 5.43: stock provenance, setup edits, and vehicle metadata are saved safely."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import pds_van_stock as van
from test_pds_van_stock import fixture_data, _move


def test_template_edit_remove_does_not_backfill_existing_vehicles(fixture_data):
    r = fixture_data
    van.template_item(van.Threshold(part_id='part-a', minimum=2, target=5), r)
    van.set_up_van(van.VanSetup(employee_id='tech-1'), r)
    van.template_item(van.Threshold(part_id='part-b', minimum=1, target=3), r)
    assert len(van.overview(r)['template_items']) == 2
    assert len(van.overview(r)['vans'][0]['items']) == 1
    van.template_item(van.Threshold(part_id='part-a', minimum=3, target=6), r)
    assert van.overview(r)['vans'][0]['items'][0]['minimum'] == 2
    assert van.remove_template_item('part-a', r)['existing_vans_unchanged']
    assert len(van.overview(r)['template_items']) == 1
    assert len(van.overview(r)['vans'][0]['items']) == 1
    _move(r, 'load', 2, '543-template-load')
    with pytest.raises(HTTPException) as err:
        van.remove_van_item('tech-1', 'part-a', r)
    assert err.value.status_code == 409
    _move(r, 'return', 2, '543-template-return')
    assert van.remove_van_item('tech-1', 'part-a', r)['ledger_preserved']
    assert not van.overview(r)['vans'][0]['items']


def test_physical_opening_count_no_warehouse_change_and_source_review(fixture_data):
    r = fixture_data
    van.set_up_van(van.VanSetup(employee_id='tech-1'), r)
    first = _move(r, 'count', 5, '543-opening-count', part='part-b')
    report = van.reconciliation(r)
    item = next(p for p in report['items'] if p['id'] == 'part-b')
    assert item['warehouse'] == 0 and item['van_total'] == 5 and item['total_tracked'] == 5
    assert report['counts']['pending_source_review'] == 1
    row = next(x for x in report['physical_count_sources'] if x['event_id'] == first['event_id'])
    assert row['source_status'] == 'unverified'
    with pytest.raises(HTTPException) as err:
        van.record_source_review(first['event_id'], van.SourceReview(source_type='purchase_reference'), r)
    assert err.value.status_code == 422
    result = van.record_source_review(first['event_id'], van.SourceReview(
        source_type='existing_owned_stock', reference='Opening count - verified by office'), r)
    assert result['accounting_posted'] is False
    report2 = van.reconciliation(r)
    assert report2['counts']['pending_source_review'] == 0
    assert report2['financial_values_posted'] is False
    assert van._read(van._path(r))['events'][0]['source_status'] == 'opening_or_adjusted_count_unverified'
    assert van._read(van._path(r))['review_history'][0]['reference'] == 'Opening count - verified by office'
    # A review marked 'unknown' must remain in pending source reconciliation.
    van.record_source_review(first['event_id'], van.SourceReview(source_type='unknown', notes='Research needed'), r)
    assert van.reconciliation(r)['counts']['pending_source_review'] == 1
    assert van.overview(r)['source_review_pending'] == 1


def test_van_vehicle_information_persists_and_tech_cannot_read_sensitive_fields(fixture_data):
    r = fixture_data
    van.set_up_van(van.VanSetup(employee_id='tech-1'), r)
    payload = van.VehicleDetails(make='Ford', model='Transit', year='2024',
        license_plate='ABC123', vin='VIN-DEMO', insurance_carrier='Insurer', notes='Maintenance review')
    assert van.save_vehicle('tech-1', payload, r)['vehicle']['make'] == 'Ford'
    assert van.overview(r)['vans'][0]['vehicle']['license_plate'] == 'ABC123'
    r.state.auth_role = 'tech'
    assert van.overview(r)['vans'][0]['vehicle'] == {}
    with pytest.raises(HTTPException) as err:
        van.save_vehicle('tech-1', payload, r)
    assert err.value.status_code == 403
    with pytest.raises(HTTPException) as err:
        van.reconciliation(r)
    assert err.value.status_code == 403
    r.session['active_platform'] = 'sdc'
    with pytest.raises(HTTPException) as err:
        van.overview(r)
    assert err.value.status_code == 403


def test_existing_usage_and_transfer_are_quantity_only(fixture_data):
    r = fixture_data
    van.set_up_van(van.VanSetup(employee_id='tech-1'), r)
    assert _move(r, 'load', 4, '543-load')['van_quantity'] == 4
    after = van.reconciliation(r)
    first = next(p for p in after['items'] if p['id'] == 'part-a')
    assert (first['warehouse'], first['van_total'], first['total_tracked']) == (6, 4, 10)
    _move(r, 'used', 1, '543-use-on-job')
    after = van.reconciliation(r)
    item = next(p for p in after['items'] if p['id'] == 'part-a')
    assert (item['warehouse'], item['van_total'], item['total_tracked']) == (6, 3, 9)
    assert after['financial_values_posted'] is False
