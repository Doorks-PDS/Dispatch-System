"""Offline safety checks for a bounded, read-only QBO duplicate preflight."""
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from app.services import pds_qbo_collision_check as checker


def req(role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role, auth_user={'id': 'admin'}),
                           session={'active_platform': 'pds'})


def setup(monkeypatch):
    # Stub only the *source preparation* check. Real preview checks are
    # covered separately; this unit isolates the remote read-only query.
    monkeypatch.setattr(checker.preview, 'preview_invoice', lambda r, n: {'pds_number': n})
    monkeypatch.setattr(checker.preview, 'preview_supplier_po', lambda r, n: {'pds_number': n})
    monkeypatch.setattr(checker.qb, '_mode', lambda r: 'online')
    monkeypatch.setattr(checker.connection, '_environment', lambda: 'sandbox')
    monkeypatch.setattr(checker.connection, 'configuration', lambda r: {
        'authorized': True, 'last_read_only_verification': 1,
        'environment': 'sandbox', 'company_id': '12345'})
    monkeypatch.setattr(checker.connection, '_access_token', lambda r: ('fake-token', '12345'))


def test_detects_existing_qbo_invoice_without_posting(monkeypatch):
    setup(monkeypatch)
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n): return json.dumps({'QueryResponse': {'Invoice': [
            {'Id':'190', 'DocNumber':'JS00021', 'SyncToken':'4',
             'CustomerRef':{'value':'PDS-CUSTOMER-SECRET'}}]}}).encode()
    def open_request(request, timeout):
        requests.append(request)
        return Response()
    monkeypatch.setattr(checker, 'urlopen', open_request)
    result = checker.check(req(), 'invoice', 'js00021')
    assert result['collision_found'] and result['match_count'] == 1
    assert result['matches'] == [{'id':'190', 'doc_number':'JS00021', 'sync_token':'4'}]
    assert 'PDS-CUSTOMER-SECRET' not in str(result)
    assert not result['can_post'] and not result['provider_write_performed']
    assert len(requests) == 1 and requests[0].get_method() == 'GET'
    statement = parse_qs(urlsplit(requests[0].full_url).query)['query'][0]
    assert statement == "SELECT * FROM Invoice WHERE DocNumber = 'JS00021' MAXRESULTS 10"


def test_no_match_still_blocks_posting(monkeypatch):
    setup(monkeypatch)
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n): return b'{"QueryResponse": {}}'
    monkeypatch.setattr(checker, 'urlopen', lambda *a,**k: Response())
    result = checker.check(req(), 'supplier_po', 'PO-00021')
    assert result['collision_found'] is False
    assert result['review_required'] and not result['can_post']


def test_permissions_and_invalid_numbers_fail_before_provider_query(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(checker, 'urlopen', lambda *a, **k: pytest.fail('Unexpected provider call'))
    for role in ('tech','lead','office'):
        with pytest.raises(HTTPException) as e:
            checker.check(req(role), 'invoice', 'JS00021')
        assert e.value.status_code == 403
    for kind, number in (('invoice', "JS00021' OR '1'='1"), ('invoice','PO-00021'),
                         ('supplier_po','JS00021'), ('garbage','JS00021')):
        with pytest.raises(HTTPException) as e:
            checker.check(req(), kind, number)
        assert e.value.status_code == 422


def test_company_mismatch_and_unverified_block_lookup(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(checker.connection, '_access_token', lambda r: ('secret', '54321'))
    with pytest.raises(HTTPException) as e: checker.check(req(), 'invoice','JS00021')
    assert e.value.status_code == 409
    monkeypatch.setattr(checker.connection, 'configuration', lambda r: {'authorized': False})
    with pytest.raises(HTTPException) as e: checker.check(req(), 'invoice','JS00021')
    assert e.value.status_code == 409
