"""Offline tests: QBO provider catalog cannot write, leak details or bypass roles."""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.services import pds_qbo_catalog as catalog


def request(role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role, auth_user={'id': 'user'}),
                           session={'active_platform': 'pds'})


def connected(monkeypatch):
    monkeypatch.setattr(catalog.qb, '_mode', lambda r: 'online')
    monkeypatch.setattr(catalog.connection, '_environment', lambda: 'sandbox')
    monkeypatch.setattr(catalog.connection, 'configuration', lambda r: {
        'authorized': True, 'last_read_only_verification': 123,
        'environment': 'sandbox', 'company_id': '12345'})
    monkeypatch.setattr(catalog.connection, '_access_token', lambda r: ('fake-secret', '12345'))


def test_catalog_is_bounded_read_only_and_sanitized(monkeypatch):
    connected(monkeypatch)
    calls=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n): return json.dumps({'QueryResponse': {'Customer': [
            {'Id': '10', 'DisplayName': 'Sample customer', 'Active': True,
             'PrimaryEmailAddr': {'Address': 'private@example.com'}, 'Balance': 999}]}}).encode()
    def fake_open(req, timeout):
        calls.append(req)
        return Response()
    monkeypatch.setattr(catalog, 'urlopen', fake_open)
    result=catalog.catalog(request(), 'customers', start=1, limit=50)
    assert len(calls)==1 and calls[0].get_method()=='GET'
    assert 'MAXRESULTS+50' in calls[0].full_url
    assert result['records']==[{'Id': '10', 'DisplayName': 'Sample customer', 'Active': True}]
    assert result['read_only'] and not result['mapping_saved'] and not result['provider_write_performed']
    assert 'private@example.com' not in str(result)


def test_rejects_bad_catalog_page_and_unverified_account(monkeypatch):
    connected(monkeypatch)
    for kind, start, limit in [('invoices', 1, 100), ('vendors', 0, 100), ('vendors', 1, 101), ('vendors', 1001, 10)]:
        with pytest.raises(HTTPException) as e: catalog.catalog(request(), kind, start=start, limit=limit)
        assert e.value.status_code==422
    monkeypatch.setattr(catalog.connection, 'configuration', lambda r: {'authorized': False})
    with pytest.raises(HTTPException) as e: catalog.catalog(request(), 'vendors')
    assert e.value.status_code==409


def test_role_guard_and_company_binding(monkeypatch):
    connected(monkeypatch)
    with pytest.raises(HTTPException) as e: catalog.catalog(request('lead'), 'vendors')
    assert e.value.status_code==403
    monkeypatch.setattr(catalog.connection, '_access_token', lambda r: ('fake-secret', 'other'))
    with pytest.raises(HTTPException) as e: catalog.catalog(request(), 'vendors')
    assert e.value.status_code==409
