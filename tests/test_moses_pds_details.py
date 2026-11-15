"""Rev 59 verified PDS job-detail lookup is workspace-scoped and bounded."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers.doorks_assistant import _execute_pds_tool


class Store:
    def __init__(self):
        self.jobs = {'p-1': {'id': 'p-1', 'job_number': '1126-01',
            'customer': 'PDS Customer', 'status': 'Quote Sent',
            'address': 'PDS Only Lane', 'estimate_number': 'RE00075',
            'approved': False, 'private_token': 'SECRET_PRIVATE',
            'job_notes': 'PRIVATE_INTERNAL_NOTES',
            'completion_forms': [{'notes': 'SECRET_FORM_DATA'}],
            'status_history': [{'from': 'Dispatch', 'to': 'Quote Sent', 'changed_at': '2026-11-11'}] * 9}}
        self.calls = 0

    def list_jobs(self):
        return [deepcopy(job) for job in self.jobs.values()]

    def get_job(self, identifier):
        self.calls += 1
        return deepcopy(self.jobs.get(identifier))


def make_request(platform='pds', role='office_admin'):
    store = Store()
    req = SimpleNamespace(state=SimpleNamespace(auth_user='admin', auth_role=role),
        session={'active_platform': platform},
        app=SimpleNamespace(state=SimpleNamespace(calendar_store=store)))
    return req, store


def test_verified_detail_contains_only_allowlisted_pds_fields():
    req, store = make_request()
    result = _execute_pds_tool(req, 'get_pds_job_details', {'record_id': 'p-1'})
    assert result['verified'] and result['read_only']
    assert result['job']['estimate_number'] == 'RE00075'
    assert result['job']['status'] == 'Quote Sent'
    assert result['job']['status_history_count'] == 9
    assert len(result['job']['recent_status_history']) == 5
    assert result['job']['recent_status_history'][0]['changed_at'] == '2026-11-11'
    assert result['job']['completion_form_count'] == 1
    for secret in ('SECRET_PRIVATE', 'PRIVATE_INTERNAL_NOTES', 'SECRET_FORM_DATA'):
        assert secret not in str(result)
    assert store.calls == 1


def test_detail_requires_exact_real_id_and_avoids_other_platforms():
    req, _ = make_request()
    for bad in ('PDS Customer', 'missing', '', 'x' * 81):
        result = _execute_pds_tool(req, 'get_pds_job_details', {'record_id': bad})
        assert result['read_only'] and 'error' in result
    for platform, role in (('sdc', 'office_admin'), ('doorks', 'office_admin'), ('pds', 'technician')):
        req, _ = make_request(platform, role)
        with pytest.raises(HTTPException) as err:
            _execute_pds_tool(req, 'get_pds_job_details', {'record_id': 'p-1'})
        assert err.value.status_code == 403


def test_unexpected_record_and_bad_arguments_fail_closed():
    req, store = make_request()
    store.get_job = lambda _id: {'id': 'different', 'secret': 'private'}
    assert 'error' in _execute_pds_tool(req, 'get_pds_job_details', {'record_id': 'p-1'})
    assert 'error' in _execute_pds_tool(req, 'get_pds_job_details', {'query': 'p-1'})
    assert 'error' in _execute_pds_tool(req, 'get_pds_job_details', None)
