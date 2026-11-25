"""Offline regression tests: independent purchasing supplier identities."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services import pds_qbo_master_links as master
from app.services.pds_qbo_sync_readiness import identify_party


def request(tmp_path):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


def test_supplier_source_is_independent_of_service_vendors(tmp_path):
    supplier = tmp_path / 'pds_suppliers'
    supplier.mkdir()
    (supplier / 'records.json').write_text(json.dumps([{'id':'supplier-1','name':'Door Parts Co'}]))
    service = tmp_path / 'pds_service_vendors'
    service.mkdir()
    (service / 'records.json').write_text(json.dumps([{'id':'service-1','name':'Field Installer'}]))
    assert master._sources(request(tmp_path), 'suppliers')[0]['pds_id'] == 'supplier-1'
    assert master._sources(request(tmp_path), 'vendors')[0]['pds_id'] == 'service-1'
    assert master.KINDS['suppliers'][0] == 'Vendor'


def test_supplier_list_missing_is_read_only(tmp_path):
    assert master._sources(request(tmp_path), 'suppliers') == []
    assert not (tmp_path / 'pds_suppliers').exists()


def test_supplier_invalid_payload_fails_closed(tmp_path):
    p = tmp_path / 'pds_suppliers'
    p.mkdir()
    (p / 'records.json').write_text('{bad')
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        master._sources(request(tmp_path), 'suppliers')
    assert error.value.status_code == 503


ROWS = [{'pds_id':'supplier-1', 'name':'Door Parts Co','active': True},
        {'pds_id':'supplier-2', 'name':'Door Parts Co','active': True}]
LINK = {'suppliers:supplier-1': {'kind':'suppliers','pds_id':'supplier-1',
    'source_name':'Door Parts Co','provider_name':'Door Parts Co',
    'provider_id':'345','company_id':'100','environment':'sandbox'}}


def resolve(**kwargs):
    return identify_party('Door Parts Co', ROWS, LINK, kind='suppliers',
                          company='100', environment='sandbox', **kwargs)


def test_explicit_supplier_id_uses_approved_link():
    r = resolve(source_id='supplier-1')
    assert r['provider_id'] == '345'
    assert r['status'] == 'approved_master_link'


def test_name_only_duplicate_is_ambiguous():
    assert resolve()['status'] == 'ambiguous_source'


def test_wrong_supplier_id_is_not_guessed():
    assert resolve(source_id='supplier-404')['status'] == 'source_id_name_mismatch'


def test_other_supplier_is_not_inferred_from_name():
    assert resolve(source_id='supplier-2')['status'] == 'approval_required'


def test_supplier_rename_with_existing_id_is_rejected():
    changed = [dict(ROWS[0], name='Door Parts Co NEW')]
    result = identify_party('Door Parts Co', changed, LINK, kind='suppliers',
                            company='100', environment='sandbox', source_id='supplier-1')
    assert result['status'] == 'source_id_name_mismatch'


def test_wrong_qbo_company_does_not_reuse_approval():
    result = identify_party('Door Parts Co', ROWS, LINK, kind='suppliers',
                            company='101', environment='sandbox', source_id='supplier-1')
    assert result['provider_id'] is None


def test_no_live_api_needed_for_source_review(tmp_path):
    supplier = tmp_path / 'pds_suppliers'
    supplier.mkdir()
    (supplier / 'records.json').write_text(json.dumps([{'id':'supplier-1','name':'Door Parts Co'}]))
    with patch.object(master, '_company', return_value=('100','sandbox','fake')):
        with patch.object(master.qb, '_admin'):
            overview = master.overview(request(tmp_path), 'suppliers')
    assert overview['records'][0]['link_status'] == 'unlinked'
    assert overview['provider_writes'] is False
