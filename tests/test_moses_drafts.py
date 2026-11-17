from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import moses_drafts as m


class Calendar:
    def __init__(self, jobs):
        self.jobs = jobs
        self.writes = 0

    def list_jobs(self):
        return self.jobs

    def get_job(self, job_id):
        return next((j for j in self.jobs if j['id'] == job_id), None)


@pytest.fixture
def env(tmp_path):
    jobs = [
        {'id': 'j1', 'job_number': 'J-1', 'customer': 'Example Inc', 'status': 'Quote',
         'completion_forms': [{'id': 'f1', 'ready_to_quote': True, 'recommendations': 'Replace damaged operator', 'parts_required': 'operator'}]},
        {'id': 'j2', 'job_number': 'J-2', 'status': 'Quote', 'completion_forms': [{'id': 'f2', 'ready_to_quote': False, 'recommendations': 'Repair'}]},
        {'id': 'j3', 'job_number': 'J-3', 'status': 'Complete', 'completion_forms': [{'id': 'f3', 'ready_to_quote': True, 'recommendations': 'Repair'}]},
    ]
    store = Calendar(jobs)
    req = SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'office'}, auth_role='office_admin'),
                          session={'active_platform': 'pds'},
                          app=SimpleNamespace(state=SimpleNamespace(calendar_store=store, data_dir=tmp_path)))
    return req, store


def test_prepare_persistent_and_idempotent(env):
    req, store = env
    first = m.prepare_batch(req)
    assert first['created'] == 1
    assert m.prepare_batch(req)['created'] == 0
    assert m.list_drafts(req)['count'] == 1
    assert store.writes == 0
    assert m._file(req).is_file()


def test_edit_survives_request_and_conflict(env):
    req, _ = env
    item = m.prepare_batch(req)['items'][0]
    updated = m.update_draft(item['id'], m.DraftEdit(version=1, scope='Replace operator with approved part', parts_review='hold', freight_review='hold'), req)['item']
    assert updated['version'] == 2
    assert m.list_drafts(req)['items'][0]['scope'] == 'Replace operator with approved part'
    with pytest.raises(HTTPException) as e:
        m.update_draft(item['id'], m.DraftEdit(version=1, scope='stale'), req)
    assert e.value.status_code == 409


def test_approve_requires_review_and_approves_no_real_document(env):
    req, store = env
    item = m.prepare_batch(req)['items'][0]
    with pytest.raises(HTTPException) as e:
        m.decide_draft(item['id'], m.DraftDecision(version=1, approve=True), req)
    assert e.value.status_code == 409
    edited = m.update_draft(item['id'], m.DraftEdit(version=1, scope='Replace operator', parts_review='hold', freight_review='not_required'), req)['item']
    approved = m.decide_draft(item['id'], m.DraftDecision(version=edited['version'], approve=True), req)
    assert approved['item']['state'] == 'ready_for_estimator'
    assert not approved['document_created'] and not approved['email_sent']
    assert store.writes == 0
    with pytest.raises(HTTPException) as e:
        m.decide_draft(item['id'], m.DraftDecision(version=approved['item']['version'], approve=True), req)
    assert e.value.status_code == 409


def test_job_change_blocks_approval(env):
    req, store = env
    item = m.prepare_batch(req)['items'][0]
    updated = m.update_draft(item['id'], m.DraftEdit(version=1, scope='Replace', parts_review='hold', freight_review='hold'), req)['item']
    store.jobs[0]['completion_forms'][0]['ready_to_quote'] = False
    with pytest.raises(HTTPException) as e:
        m.decide_draft(item['id'], m.DraftDecision(version=updated['version'], approve=True), req)
    assert e.value.status_code == 409


def test_decline_preserved_and_rescan_does_not_recreate(env):
    req, _ = env
    item = m.prepare_batch(req)['items'][0]
    decision = m.decide_draft(item['id'], m.DraftDecision(version=1, approve=False), req)
    assert decision['item']['state'] == 'declined'
    assert m.prepare_batch(req)['created'] == 0


def test_permission_and_workspace_isolation(env):
    req, _ = env
    req.state.auth_role = 'tech'
    with pytest.raises(HTTPException) as e: m.prepare_batch(req)
    assert e.value.status_code == 403
    req.state.auth_role = 'office_admin'
    req.session['active_platform'] = 'doorks'
    with pytest.raises(HTTPException) as e: m.list_drafts(req)
    assert e.value.status_code == 403


def test_corrupt_storage_fails_closed(env):
    req, _ = env
    target = m._file(req)
    target.parent.mkdir(parents=True)
    target.write_text('NOT JSON')
    with pytest.raises(HTTPException) as e: m.prepare_batch(req)
    assert e.value.status_code == 503
    assert target.read_text() == 'NOT JSON'
