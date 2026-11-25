"""Offline regression tests for master identity matching. No QBO writes."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services import pds_qbo_master_links as master


class FakeCRM:
    def list_customers(self):
        return [{'id': 'cust-a', 'company_name': 'Cheesecake Factory', 'active': True},
                {'id': 'cust-b', 'company_name': 'Panda', 'active': True}]


def req(tmp_path, role='office_admin'):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, crm_store=FakeCRM())),
        session={'active_platform': 'pds'},
        state=SimpleNamespace(auth_role=role, auth_user={'id': 'office-1'}))


def company(request):
    return ('1234567', 'sandbox', 'token')


class Response:
    def __init__(self, kind='Customer', name='Cheesecake Factory', id='12', active=True):
        self.payload = json.dumps({'QueryResponse': {kind: [{'Id': id, 'DisplayName' if kind != 'Item' else 'Name': name, 'Active': active}]}}).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, n): return self.payload


def test_overview_local_customer_records_without_migration(tmp_path):
    r = req(tmp_path)
    with patch.object(master, '_company', company):
        result = master.overview(r, 'customers')
    assert result['total'] == 2
    assert result['records'][0]['link_status'] == 'unlinked'
    assert result['automatic_sync_enabled'] is False
    assert not (tmp_path / 'pds_qbo_master_links.json').exists()


def test_approval_cannot_be_done_by_technician(tmp_path):
    r = req(tmp_path, 'tech')
    with pytest.raises(HTTPException) as exc:
        master.approve(r, 'customers', 'cust-a', '12', confirm=True)
    assert exc.value.status_code == 403


def test_confirm_and_numeric_id_required(tmp_path):
    r = req(tmp_path)
    for pid, confirm in [('12', False), ('abc', True)]:
        with pytest.raises(HTTPException) as exc:
            master.approve(r, 'customers', 'cust-a', pid, confirm=confirm)
        assert exc.value.status_code == 422


def test_matching_customer_id_saved_once_and_conflicts_blocked(tmp_path):
    r = req(tmp_path)
    with patch.object(master, '_company', company), patch.object(master, 'urlopen', return_value=Response()):
        result = master.approve(r, 'customers', 'cust-a', '12', confirm=True)
        assert result['status'] == 'linked'
        assert master.approve(r, 'customers', 'cust-a', '12', confirm=True)['status'] == 'already_linked'
        with pytest.raises(HTTPException) as exc:
            master.approve(r, 'customers', 'cust-b', '12', confirm=True)
        assert exc.value.status_code == 409
        overview = master.overview(r, 'customers')
        assert overview['records'][0]['provider_id'] == '12'
        assert overview['records'][1]['link_status'] == 'unlinked'
    assert (tmp_path / 'pds_qbo_master_links.json').exists()


def test_wrong_name_cannot_link(tmp_path):
    r = req(tmp_path)
    with patch.object(master, '_company', company), patch.object(master, 'urlopen', return_value=Response(name='Other Customer')):
        with pytest.raises(HTTPException) as exc:
            master.approve(r, 'customers', 'cust-a', '12', confirm=True)
        assert exc.value.status_code == 409
    assert not (tmp_path / 'pds_qbo_master_links.json').exists()


def test_pds_source_rename_stales_link(tmp_path):
    r = req(tmp_path)
    with patch.object(master, '_company', company), patch.object(master, 'urlopen', return_value=Response()):
        master.approve(r, 'customers', 'cust-a', '12', confirm=True)
    r.app.state.crm_store.list_customers = lambda: [{'id':'cust-a','company_name':'Cheesecake Factory Inc.'}]
    with patch.object(master, '_company', company):
        rows = master.overview(r, 'customers')['records']
    assert rows[0]['link_status'] == 'stale_requires_review' and rows[0]['provider_id'] is None


def test_wrong_company_shows_stale(tmp_path):
    r = req(tmp_path)
    with patch.object(master, '_company', company), patch.object(master, 'urlopen', return_value=Response()):
        master.approve(r, 'customers', 'cust-a', '12', confirm=True)
    with patch.object(master, '_company', lambda request: ('other', 'sandbox', 'token')):
        row = master.overview(r, 'customers')['records'][0]
    assert row['link_status'] == 'stale_requires_review'
