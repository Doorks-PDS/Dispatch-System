"""Moses broad business discovery must not cross tenant or reveal raw fields."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_records as records


def req(tmp_path, platform='sdc', role='office_admin', user=True):
    return SimpleNamespace(
        session={'active_platform': platform},
        state=SimpleNamespace(auth_user={'id': '1'} if user else None, auth_role=role),
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)))


def seed(tmp_path, platform, kind, rows):
    path = tmp_path / 'business_workspaces' / platform / (kind + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding='utf-8')


def test_sdc_search_detail_has_exact_internal_id_but_no_internal_fields(tmp_path):
    seed(tmp_path, 'sdc', 'estimates_invoices', [
        {'id': 'abc', 'invoice_number': 'INV-100', 'customer': 'Jane', 'total': 123,
         'private_token': 'NEVER EXPOSE', 'notes': 'DO NOT EXPOSE', 'pdf_blob': 'HIDDEN'},
        {'id': 'other', 'invoice_number': 'INV-101', 'customer': 'John'}])
    r = req(tmp_path)
    assert 'estimates_invoices' in records.collections(r)['collections']
    found = records.search(r, 'estimates_invoices', 'INV-100')
    assert found['matching_count'] == 1
    assert found['examples'][0]['id'] == 'abc'
    detail = records.details(r, 'estimates_invoices', 'abc')
    assert detail['verified'] and detail['record']['total'] == '123'
    assert 'NEVER EXPOSE' not in str(detail) and 'DO NOT EXPOSE' not in str(detail)
    assert 'HIDDEN' not in str(detail)


def test_workspace_scoping_and_sensitive_collections(tmp_path):
    seed(tmp_path, 'sdc', 'customers', [{'id': 'sdc1', 'name': 'SDC confidential'}])
    seed(tmp_path, 'doorks', 'customers', [{'id': 'd1', 'name': 'Doorks confidential'}])
    for platform, own, other in [('sdc', 'sdc1', 'd1'), ('doorks', 'd1', 'sdc1')]:
        r = req(tmp_path, platform)
        results = records.search(r, 'customers', 'confidential')
        assert [x['id'] for x in results['examples']] == [own]
        with pytest.raises(HTTPException) as error:
            records.details(r, 'customers', other)
        assert error.value.status_code == 404
    for sensitive in ('employees', 'payroll', 'stock_adjustments'):
        with pytest.raises(HTTPException) as error:
            records.search(req(tmp_path, 'doorks'), sensitive, 'anything')
        assert error.value.status_code == 403


def test_auth_and_validation(tmp_path):
    for r in (req(tmp_path, 'sdc', role='technician'), req(tmp_path, user=False)):
        with pytest.raises(HTTPException) as error:
            records.collections(r)
        assert error.value.status_code in (401, 403)
    with pytest.raises(HTTPException):
        records.collections(req(tmp_path, 'pds'))
    with pytest.raises(HTTPException) as error:
        records.search(req(tmp_path), 'vendors', '')
    assert error.value.status_code == 422
    with pytest.raises(HTTPException) as error:
        records.details(req(tmp_path), 'vendors', '../x')
    assert error.value.status_code == 404


def test_search_is_bounded_and_disallows_notes_as_search_key(tmp_path):
    seed(tmp_path, 'doorks', 'purchase_orders', [
        {'id': str(i), 'po_number': f'PO-{i}', 'vendor_name': 'Tools',
         'notes': 'secret_only'} for i in range(20)])
    r = req(tmp_path, 'doorks')
    assert records.search(r, 'purchase_orders', 'secret_only')['matching_count'] == 0
    result = records.search(r, 'purchase_orders', 'Tools')
    assert result['matching_count'] == 20 and len(result['examples']) == 8
