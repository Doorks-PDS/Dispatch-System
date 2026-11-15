"""Rev 58 PDS actions: no direct execution from a chat tool or cross-workspace access."""
from copy import deepcopy
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_pds_actions as actions
from app.routers.doorks_assistant import _execute_pds_tool


class Store:
    def __init__(self):
        self._lock = RLock()
        self.jobs = {'p-1': {'id': 'p-1', 'job_number': '1126-01', 'customer': 'PDS Only',
                             'status': 'Dispatch', 'status_history': []}}
        self.calls = 0
        self.fail_after_save = False

    def get_job(self, id):
        return deepcopy(self.jobs.get(id))

    def update_job(self, id, patch):
        self.calls += 1
        job = self.jobs[id]
        job['status_history'].append({'old': job['status'], 'new': patch['status']})
        job['status'] = patch['status']
        job['last_modified_by'] = patch.get('last_modified_by')
        if self.fail_after_save:
            raise RuntimeError('Simulated failure after PDS saved')
        return deepcopy(job)


def request(tmp_path, platform='pds', role='office_admin'):
    store = Store()
    req = SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'operator'}, auth_role=role),
                          session={'active_platform': platform},
                          app=SimpleNamespace(state=SimpleNamespace(calendar_store=store,
                                                                    data_dir=tmp_path)))
    return req, store


def test_requires_explicit_flag_and_active_pds_admin(monkeypatch, tmp_path):
    monkeypatch.delenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', raising=False)
    req, store = request(tmp_path)
    with pytest.raises(HTTPException) as exc:
        actions.propose(req, 'p-1', 'Quote')
    assert exc.value.status_code == 503 and store.calls == 0
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    for platform, role in (('sdc', 'office_admin'), ('doorks', 'office_admin'), ('pds', 'technician')):
        other, _ = request(tmp_path, platform, role)
        with pytest.raises(HTTPException) as exc:
            actions.pending(other)
        assert exc.value.status_code == 403


def test_proposal_and_rejection_do_not_change_job(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    req, store = request(tmp_path)
    proposed = _execute_pds_tool(req, 'propose_pds_job_status', {'record_id': 'p-1', 'new_status': 'Quote'})
    assert proposed['approval_required'] and not proposed['executed']
    assert proposed['proposal']['kind'] == 'pds_job_status'
    assert store.calls == 0 and store.get_job('p-1')['status'] == 'Dispatch'
    proposal_id = proposed['proposal']['id']
    assert actions.pending(req)['count'] == 1
    result = actions.decide(req, proposal_id, False)
    assert not result['executed'] and store.calls == 0
    with pytest.raises(HTTPException) as exc:
        actions.decide(req, proposal_id, True)
    assert exc.value.status_code == 409


def test_approved_action_uses_existing_calendar_store_and_confirms(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    req, store = request(tmp_path)
    proposal = actions.propose(req, 'p-1', 'Quote')['proposal']
    result = actions.decide(req, proposal['id'], True)
    assert result['executed'] and result['confirmed_status'] == 'Quote'
    assert store.calls == 1
    assert store.get_job('p-1')['status_history'] == [{'old': 'Dispatch', 'new': 'Quote'}]
    with pytest.raises(HTTPException) as exc:
        actions.decide(req, proposal['id'], True)
    assert exc.value.status_code == 409 and store.calls == 1
    assert 'business_workspaces' not in str(actions._file(req))


def test_stale_version_blocks_and_does_not_apply(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    req, store = request(tmp_path)
    proposal = actions.propose(req, 'p-1', 'Quote')['proposal']
    store.jobs['p-1']['customer'] = 'Someone edited the job'
    with pytest.raises(HTTPException) as exc:
        actions.decide(req, proposal['id'], True)
    assert exc.value.status_code == 409 and store.calls == 0


def test_interrupted_save_quarantines_no_duplicate_execution(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    req, store = request(tmp_path)
    proposal = actions.propose(req, 'p-1', 'Quote')['proposal']
    store.fail_after_save = True
    with pytest.raises(HTTPException) as exc:
        actions.decide(req, proposal['id'], True)
    assert exc.value.status_code == 500
    assert store.calls == 1
    pending = actions.pending(req)
    assert pending['proposals'][0]['state'] == 'needs_review'
    with pytest.raises(HTTPException):
        actions.decide(req, proposal['id'], True)
    assert store.calls == 1


def test_validation_rejects_aliases_and_nonexistent_record(monkeypatch, tmp_path):
    monkeypatch.setenv('DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED', 'true')
    req, _ = request(tmp_path)
    for status in ('Approved', 'In Progress', 'Additional Work', 'Complete/Additional Work'):
        with pytest.raises(HTTPException) as exc:
            actions.propose(req, 'p-1', status)
        assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        actions.propose(req, 'missing', 'Quote')
    assert exc.value.status_code == 404
