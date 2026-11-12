"""Moses 2.0 isolated router regression tests; no production records or AI calls."""
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.fixture
def moses(tmp_path, monkeypatch):
    """Import only the command router with deterministic file-backed storage."""
    services = types.ModuleType('app.services.moses_assist')
    services._client = lambda: None
    services.MOSES_MODEL = 'test-model'
    workspaces = types.ModuleType('app.routers.workspaces')
    def load(path):
        return json.loads(path.read_text()) if path.exists() else []
    def save(path, items):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items))
    workspaces.load, workspaces.save = load, save
    monkeypatch.setitem(sys.modules, 'app.services.moses_assist', services)
    monkeypatch.setitem(sys.modules, 'app.routers.workspaces', workspaces)
    source = Path(__file__).resolve().parents[1] / 'app/routers/moses_command.py'
    spec = importlib.util.spec_from_file_location('moses_command_test', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def request(role='office_admin', platform='sdc', user=True):
        return SimpleNamespace(
            state=SimpleNamespace(auth_user={'id': 'owner'} if user else None, auth_role=role),
            session={'active_platform': platform},
            app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))
    return module, request, tmp_path


def _task(m, req):
    return m.create_task(req, m.NewTask(capability='Marketing', title='Draft campaign', instructions='Create a post'))['task']


def test_guard_requires_admin_and_sdc(moses):
    m, req, _ = moses
    for request in [req(user=False), req(role='technician'), req(platform='pds')]:
        with pytest.raises(HTTPException) as err:
            m.list_tasks(request)
        assert err.value.status_code in (401, 403)
    assert m.list_tasks(req())['tasks'] == []


def test_create_and_persist_without_external_execution(moses):
    m, req, _ = moses
    task = _task(m, req())
    assert task['status'] == 'draft'
    assert m.list_tasks(req())['execution_enabled'] is False
    assert m.list_tasks(req())['tasks'][0]['id'] == task['id']
    assert m.command_overview(req())['external_execution_enabled'] is False


def test_approval_requires_prepared_draft_and_current_version(moses):
    m, req, _ = moses
    task = _task(m, req())
    with pytest.raises(HTTPException) as err:
        m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=0))
    assert err.value.status_code == 409
    m.edit_draft(task['id'], req(), m.Revision(draft='Review this marketing copy.', expected_draft_version=0))
    with pytest.raises(HTTPException) as err:
        m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=0))
    assert err.value.status_code == 409
    result = m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    assert result['task']['status'] == 'approved_pending_execution'
    assert result['execution_enabled'] is False


def test_approved_internal_filing_is_idempotent(moses):
    m, req, _ = moses
    task = _task(m, req())
    m.edit_draft(task['id'], req(), m.Revision(draft='Ready for review.', expected_draft_version=0))
    m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    first = m.file_approved_deliverable(task['id'], req())
    second = m.file_approved_deliverable(task['id'], req())
    assert first['already_filed'] is False
    assert second['already_filed'] is True
    assert first['deliverable']['id'] == second['deliverable']['id']
    assert len(m.list_deliverables(req())['deliverables']) == 1


def test_rejected_tasks_cannot_be_filed(moses):
    m, req, _ = moses
    task = _task(m, req())
    m.edit_draft(task['id'], req(), m.Revision(draft='Do not publish.', expected_draft_version=0))
    m.decide_task(task['id'], req(), m.Decision(decision='reject', expected_draft_version=1))
    with pytest.raises(HTTPException) as err:
        m.file_approved_deliverable(task['id'], req())
    assert err.value.status_code == 409


def test_context_is_sdc_only_and_allowlisted(moses):
    m, req, root = moses
    sdc = root / 'business_workspaces/sdc'
    pds = root / 'business_workspaces/pds'
    sdc.mkdir(parents=True)
    pds.mkdir(parents=True)
    (sdc / 'software_leads.json').write_text(json.dumps([{'name': 'Customer', 'message': 'Inquiry', 'api_key': 'secret'}]))
    (pds / 'software_leads.json').write_text(json.dumps([{'name': 'PDS confidential'}]))
    context = m.context_preview(req())['context']
    assert context['workspace'] == 'sdc'
    sample = context['collections']['software_leads']['recent_sample'][0]
    assert sample['name'] == 'Customer'
    assert 'api_key' not in sample
    assert 'PDS confidential' not in json.dumps(context)


def test_due_dates_are_planning_only(moses):
    m, req, _ = moses
    task = _task(m, req())
    with pytest.raises(HTTPException):
        m.reschedule_task(task['id'], req(), m.Reschedule(due_at='2026-11-20T09:00:00'))
    updated = m.reschedule_task(task['id'], req(), m.Reschedule(due_at='2026-11-20T09:00:00-08:00'))
    assert updated['automatic_execution_enabled'] is False
    assert m.task_agenda(req())['automatic_execution_enabled'] is False

def test_diagnostics_do_not_create_storage_or_run_ai(moses):
    m, req, root = moses
    result = m.command_diagnostics(req())
    assert result["ok"] is True
    assert result["storage"]["tasks"]["state"] == "not_created"
    assert result["storage"]["deliverables"]["state"] == "not_created"
    assert result["external_execution_enabled"] is False
    assert not (root / "business_workspaces/sdc/moses_tasks.json").exists()
    _task(m, req())
    assert m.command_diagnostics(req())["storage"]["tasks"]["records"] == 1


def test_diagnostics_report_malformed_store_without_repairing_it(moses):
    m, req, root = moses
    sdc = root / "business_workspaces/sdc"
    sdc.mkdir(parents=True)
    path = sdc / "moses_tasks.json"
    path.write_text("{invalid json")
    result = m.command_diagnostics(req())
    assert result["ok"] is False
    assert result["storage"]["tasks"]["state"] == "invalid"
    assert path.read_text() == "{invalid json"


def test_diagnostics_require_sdc_admin(moses):
    m, req, _ = moses
    for request in (req(role="technician"), req(platform="pds"), req(user=False)):
        with pytest.raises(HTTPException):
            m.command_diagnostics(request)


def test_partial_filing_retry_repairs_task_status(moses):
    m, req, root = moses
    task = _task(m, req())
    m.edit_draft(task['id'], req(), m.Revision(draft='Approved internal draft.', expected_draft_version=0))
    m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    # Simulate interruption after deliverables write but before task state update.
    first = m.file_approved_deliverable(task['id'], req())['deliverable']
    task_path = root / 'business_workspaces/sdc/moses_tasks.json'
    tasks = json.loads(task_path.read_text())
    tasks[0]['status'] = 'approved_pending_execution'
    task_path.write_text(json.dumps(tasks))
    recovered = m.file_approved_deliverable(task['id'], req())
    assert recovered['already_filed'] is True
    assert recovered['deliverable']['id'] == first['id']
    assert m.list_tasks(req())['tasks'][0]['status'] == 'filed_internal'
    assert len(m.list_deliverables(req())['deliverables']) == 1


def test_router_http_endpoints_and_workspace_gate(moses):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.middleware.sessions import SessionMiddleware
    m, _, root = moses
    app = FastAPI()
    app.state.data_dir = str(root)
    @app.middleware('http')
    async def auth(request, call_next):
        request.state.auth_user = {'id': 'owner'}
        request.state.auth_role = 'office_admin'
        request.session['active_platform'] = 'sdc'
        return await call_next(request)
    app.add_middleware(SessionMiddleware, secret_key='test-only-secret')
    app.include_router(m.router)
    with TestClient(app) as client:
        response = client.get('/moses-command/diagnostics')
        assert response.status_code == 200
        assert response.json()['external_execution_enabled'] is False
        response = client.post('/moses-command/tasks', json={
            'capability': 'Marketing', 'title': 'Draft a campaign', 'instructions': 'Draft only'})
        assert response.status_code == 201
        assert client.get('/moses-command/tasks').json()['tasks'][0]['title'] == 'Draft a campaign'
        assert client.get('/moses-command/overview').json()['total_tasks'] == 1


def test_read_only_endpoints_never_create_sdc_directory(moses):
    m, req, root = moses
    sdc = root / 'business_workspaces' / 'sdc'
    assert not sdc.exists()
    assert m.list_tasks(req())['tasks'] == []
    assert m.command_overview(req())['total_tasks'] == 0
    assert m.task_agenda(req())['agenda'] == []
    assert m.business_briefing(req())['tasks']['filed_deliverables'] == 0
    assert m.context_preview(req())['context']['workspace'] == 'sdc'
    assert m.list_deliverables(req())['deliverables'] == []
    assert not sdc.exists()
    _task(m, req())
    assert (sdc / 'moses_tasks.json').exists()


def test_real_workspace_storage_round_trip(tmp_path, monkeypatch):
    """Use the actual existing Doorks workspace load/save, not the fixture's stub."""
    import importlib.util
    source = Path(__file__).resolve().parents[1] / 'app/routers/workspaces.py'
    if not source.exists():
        pytest.skip('Full Doorks workspaces module not present in patch-only checkout')
    spec = importlib.util.spec_from_file_location('real_workspaces_for_moses', source)
    workspace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workspace)
    services = types.ModuleType('app.services.moses_assist')
    services._client = lambda: None
    services.MOSES_MODEL = 'test-model'
    monkeypatch.setitem(sys.modules, 'app.services.moses_assist', services)
    monkeypatch.setitem(sys.modules, 'app.routers.workspaces', workspace)
    source = Path(__file__).resolve().parents[1] / 'app/routers/moses_command.py'
    spec = importlib.util.spec_from_file_location('real_moses_storage_test', source)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    request = SimpleNamespace(state=SimpleNamespace(auth_user={'id':'owner'},auth_role='office_admin'),
        session={'active_platform':'sdc'},app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))
    task = m.create_task(request, m.NewTask(capability='Marketing',title='Storage round trip'))['task']
    m.edit_draft(task['id'],request,m.Revision(draft='Approved draft',expected_draft_version=0))
    m.decide_task(task['id'],request,m.Decision(decision='approve',expected_draft_version=1))
    m.file_approved_deliverable(task['id'],request)
    assert m.list_tasks(request)['tasks'][0]['status']=='filed_internal'
    assert len(m.list_deliverables(request)['deliverables'])==1
    assert not (tmp_path/'business_workspaces/sdc/moses_tasks.json.tmp').exists()


def test_malformed_moses_rows_fail_closed_without_overwrite(moses):
    m, req, root = moses
    sdc = root / "business_workspaces/sdc"
    sdc.mkdir(parents=True)
    path = sdc / "moses_tasks.json"
    original = '[{"id":"valid"}, null]'
    path.write_text(original)
    for endpoint in (m.list_tasks, m.command_overview, m.task_agenda, m.business_briefing):
        with pytest.raises(HTTPException) as exc:
            endpoint(req())
        assert exc.value.status_code == 500
    with pytest.raises(HTTPException) as exc:
        m.create_task(req(), m.NewTask(capability="Marketing", title="Test task"))
    assert exc.value.status_code == 500
    assert path.read_text() == original
    diagnostics = m.command_diagnostics(req())
    assert diagnostics["ok"] is False
    assert diagnostics["storage"]["tasks"]["state"] == "invalid"


def test_malformed_deliverable_rows_fail_closed(moses):
    m, req, root = moses
    sdc = root / "business_workspaces/sdc"
    sdc.mkdir(parents=True)
    path = sdc / "moses_deliverables.json"
    path.write_text('[42]')
    with pytest.raises(HTTPException) as exc:
        m.list_deliverables(req())
    assert exc.value.status_code == 500
    assert m.command_diagnostics(req())["storage"]["deliverables"]["state"] == "invalid"
    assert path.read_text() == '[42]'


def test_malformed_sdc_context_fails_closed_without_changing_records(moses):
    m, req, root = moses
    sdc = root / 'business_workspaces/sdc'
    sdc.mkdir(parents=True)
    path = sdc / 'orders.json'
    for invalid in ('{invalid', '[{"order_id":"ok"},null]'):
        path.write_text(invalid)
        with pytest.raises(HTTPException) as exc:
            m.context_preview(req())
        assert exc.value.status_code == 500
        assert path.read_text() == invalid


def test_context_does_not_expose_private_fields_or_other_workspaces(moses):
    m, req, root = moses
    sdc = root / 'business_workspaces/sdc'
    pds = root / 'business_workspaces/doorks'
    sdc.mkdir(parents=True)
    pds.mkdir(parents=True)
    (sdc / 'software_leads.json').write_text(json.dumps([
        {'name': 'Lead A', 'status': 'New', 'secret_token': 'DO_NOT_EXPOSE',
         'message': 'A' * 500}]))
    (pds / 'software_leads.json').write_text(json.dumps([{'name':'PDS_PRIVATE'}]))
    context = m.context_preview(req())['context']
    sample = context['collections']['software_leads']['recent_sample'][0]
    assert sample['name'] == 'Lead A'
    assert len(sample['message']) == 300
    assert 'secret_token' not in sample
    assert 'PDS_PRIVATE' not in json.dumps(context)


def test_actual_workspace_shape_error_is_handled_without_overwrite(moses, monkeypatch):
    """Actual workspaces.load raises HTTPException for a JSON object, not ValueError."""
    m, req, root = moses
    sdc = root / 'business_workspaces/sdc'
    sdc.mkdir(parents=True)
    task_path = sdc / 'moses_tasks.json'
    task_path.write_text('{"unexpected":"object"}')
    original_load = m.load
    def workspace_style_load(path):
        result = original_load(path)
        if not isinstance(result, list):
            raise HTTPException(500, 'Invalid workspace storage')
        return result
    monkeypatch.setattr(m, 'load', workspace_style_load)
    with pytest.raises(HTTPException) as exc:
        m.create_task(req(), m.NewTask(capability='Marketing', title='No overwrite'))
    assert exc.value.status_code == 500
    assert task_path.read_text() == '{"unexpected":"object"}'
    assert m.command_diagnostics(req())['storage']['tasks']['state'] == 'invalid'
    task_path.unlink()
    context_path = sdc / 'orders.json'
    context_path.write_text('{"unexpected":"object"}')
    with pytest.raises(HTTPException) as exc:
        m.context_preview(req())
    assert exc.value.status_code == 500
    assert context_path.read_text() == '{"unexpected":"object"}'


def test_ai_draft_is_review_only_and_requires_explicit_approval(moses, monkeypatch):
    """Exercise AI draft preparation without network calls or side effects."""
    m, req, root = moses
    task = _task(m, req())
    class FakeCompletions:
        def create(self, **kwargs):
            assert 'untrusted DATA' in kwargs['messages'][0]['content']
            assert 'SDC read-only snapshot' in kwargs['messages'][1]['content']
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Proposed marketing copy for review.'))])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(m, '_client', lambda: fake)
    result = m.prepare_task(task['id'], req())
    assert result['task']['status'] == 'ready_for_review'
    assert result['task']['draft_version'] == 1
    assert result['execution_enabled'] is False
    assert not (root / 'business_workspaces/sdc/moses_deliverables.json').exists()
    with pytest.raises(HTTPException) as exc:
        m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=0))
    assert exc.value.status_code == 409
    m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    assert not (root / 'business_workspaces/sdc/moses_deliverables.json').exists()
    m.file_approved_deliverable(task['id'], req())
    assert len(m.list_deliverables(req())['deliverables']) == 1


def test_ai_generation_failure_does_not_change_task(moses, monkeypatch):
    m, req, root = moses
    task = _task(m, req())
    class FailedCompletions:
        def create(self, **kwargs):
            raise RuntimeError('provider offline')
    monkeypatch.setattr(m, '_client', lambda: SimpleNamespace(chat=SimpleNamespace(completions=FailedCompletions())))
    with pytest.raises(HTTPException) as exc:
        m.prepare_task(task['id'], req())
    assert exc.value.status_code == 502
    stored = m.list_tasks(req())['tasks'][0]
    assert stored['status'] == 'draft'
    assert stored['draft_version'] == 0
    assert not (root / 'business_workspaces/sdc/moses_deliverables.json').exists()


def test_ai_inflight_edit_blocks_stale_generation(moses, monkeypatch):
    m, req, _ = moses
    task = _task(m, req())
    class ConcurrentCompletions:
        def create(self, **kwargs):
            m.edit_draft(task['id'], req(), m.Revision(draft='Newer human version', expected_draft_version=0))
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Stale AI version'))])
    monkeypatch.setattr(m, '_client', lambda: SimpleNamespace(chat=SimpleNamespace(completions=ConcurrentCompletions())))
    with pytest.raises(HTTPException) as exc:
        m.prepare_task(task['id'], req())
    assert exc.value.status_code == 409
    saved = m.list_tasks(req())['tasks'][0]
    assert saved['draft_output'] == 'Newer human version'
    assert saved['draft_version'] == 1


def test_full_application_session_auth_and_sdc_isolation(tmp_path, monkeypatch):
    """Exercise real main.py middleware, session cookies and Moses routes.

    This test is intended to run inside the complete Doorks repository. It
    never uses production storage or a real user account.
    """
    import base64
    import importlib
    import os
    from itsdangerous import TimestampSigner
    from fastapi.testclient import TestClient

    app_main = importlib.import_module('main')
    original_store = app_main.app.state.users_store
    original_dir = app_main.app.state.data_dir
    class FakeUsers:
        def get_by_id(self, user_id):
            if user_id == 'admin':
                return {'id': 'admin', 'username': 'integration-test', 'role': 'office_admin', 'active': True}
            if user_id == 'tech':
                return {'id': 'tech', 'username': 'integration-test-tech', 'role': 'tech', 'active': True}
            return None

    def session_cookie(user_id, platform):
        raw = base64.b64encode(json.dumps({'user_id': user_id, 'active_platform': platform}).encode())
        secret = os.getenv('DOORKS_SESSION_SECRET', 'doorks-local-dev-secret-jason-2026')
        return TimestampSigner(secret).sign(raw).decode()

    try:
        app_main.app.state.users_store = FakeUsers()
        app_main.app.state.data_dir = str(tmp_path)
        with TestClient(app_main.app) as client:
            assert client.get('/moses-command/tasks').status_code == 401
            for user_id, platform in [('tech', 'sdc'), ('admin', 'pds')]:
                client.cookies.clear()
                client.cookies.set('session', session_cookie(user_id, platform))
                assert client.get('/moses-command/tasks').status_code == 403
                assert client.post('/moses-command/tasks', json={
                    'capability': 'Marketing', 'title': 'Unauthorized attempt'}).status_code == 403
            client.cookies.clear()
            client.cookies.set('session', session_cookie('admin', 'sdc'))
            response = client.post('/moses-command/tasks', json={
                'capability': 'Marketing', 'title': 'Safe integration test',
                'instructions': 'Do not send anything.'})
            assert response.status_code == 201, response.text
            task_id = response.json()['task']['id']
            response = client.get('/moses-command/tasks')
            assert response.status_code == 200
            assert any(t['id'] == task_id for t in response.json()['tasks'])
            response = client.get('/moses-command/diagnostics')
            assert response.status_code == 200
            assert response.json()['storage']['tasks']['records'] == 1
            assert response.json()['external_execution_enabled'] is False
        assert (tmp_path / 'business_workspaces/sdc/moses_tasks.json').is_file()
    finally:
        app_main.app.state.users_store = original_store
        app_main.app.state.data_dir = original_dir


def test_diagnostics_never_calls_ai_provider(moses, monkeypatch):
    m, req, _ = moses
    def unavailable():
        raise RuntimeError("Provider initialization failed")
    monkeypatch.setattr(m, '_client', unavailable)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    result = m.command_diagnostics(req())
    assert result['ok'] is True
    assert result['ai_configured'] is False
    monkeypatch.setenv('OPENAI_API_KEY', 'test-configured')
    assert m.command_diagnostics(req())['ai_configured'] is True

def test_diagnostics_never_discloses_ai_key(moses, monkeypatch):
    m, req, _ = moses
    monkeypatch.setenv('OPENAI_API_KEY', 'do-not-leak-this-secret')
    result = m.command_diagnostics(req())
    assert 'do-not-leak-this-secret' not in json.dumps(result)


def test_duplicate_task_identifiers_block_approval_and_writes(moses):
    m, req, root = moses
    task = _task(m, req())
    path = root / "business_workspaces/sdc/moses_tasks.json"
    original = json.loads(path.read_text())
    path.write_text(json.dumps([original[0], original[0]]))
    before = path.read_bytes()
    with pytest.raises(HTTPException) as err:
        m.create_task(req(), m.NewTask(capability="Sales", title="Another task"))
    assert err.value.status_code == 500
    with pytest.raises(HTTPException):
        m.decide_task(task["id"], req(), m.Decision(decision="approve", expected_draft_version=0))
    assert m.command_diagnostics(req())["storage"]["tasks"]["state"] == "invalid"
    assert path.read_bytes() == before


def test_missing_record_identifiers_fail_closed(moses):
    m, req, root = moses
    path = root / "business_workspaces/sdc/moses_deliverables.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"task_id": "orphan", "content": "draft"}]))
    with pytest.raises(HTTPException) as err:
        m.list_deliverables(req())
    assert err.value.status_code == 500
    assert m.command_diagnostics(req())["storage"]["deliverables"]["state"] == "invalid"


def test_duplicate_deliverable_task_links_fail_closed(moses):
    m, req, root = moses
    task = _task(m, req())
    path = root / "business_workspaces/sdc/moses_deliverables.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {"id": "first", "task_id": task["id"], "content": "Draft A"},
        {"id": "second", "task_id": task["id"], "content": "Draft B"},
    ]
    path.write_text(json.dumps(entries))
    before = path.read_bytes()
    with pytest.raises(HTTPException) as err:
        m.list_deliverables(req())
    assert err.value.status_code == 500
    assert m.command_diagnostics(req())["storage"]["deliverables"]["state"] == "invalid"
    assert path.read_bytes() == before


def test_missing_deliverable_task_link_is_not_accepted(moses):
    m, req, root = moses
    path = root / "business_workspaces/sdc/moses_deliverables.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{"id": "valid-id", "content": "Unlinked"}]))
    with pytest.raises(HTTPException) as err:
        m.list_deliverables(req())
    assert err.value.status_code == 500
    assert m.command_diagnostics(req())["storage"]["deliverables"]["state"] == "invalid"


def test_filing_recovery_refuses_mismatched_content_without_writes(moses):
    m, req, root = moses
    task = _task(m, req())
    m.edit_draft(task['id'], req(), m.Revision(draft='Approved version', expected_draft_version=0))
    m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    path = root / 'business_workspaces/sdc/moses_deliverables.json'
    path.write_text(json.dumps([{'id':'existing', 'task_id':task['id'],
        'capability':'Marketing', 'title':task['title'],
        'content':'DIFFERENT CONTENT', 'status':'internal_only'}]))
    task_path = root / 'business_workspaces/sdc/moses_tasks.json'
    before_task, before_deliverable = task_path.read_bytes(), path.read_bytes()
    with pytest.raises(HTTPException) as err:
        m.file_approved_deliverable(task['id'], req())
    assert err.value.status_code == 409
    assert task_path.read_bytes() == before_task
    assert path.read_bytes() == before_deliverable


def test_filing_recovery_refuses_wrong_deliverable_metadata(moses):
    m, req, root = moses
    task = _task(m, req())
    m.edit_draft(task['id'], req(), m.Revision(draft='Approved version', expected_draft_version=0))
    m.decide_task(task['id'], req(), m.Decision(decision='approve', expected_draft_version=1))
    path = root / 'business_workspaces/sdc/moses_deliverables.json'
    for field, wrong in [('title','Wrong title'), ('capability','Accounting'), ('status','published')]:
        record = {'id':'existing', 'task_id':task['id'], 'capability':'Marketing',
                  'title':task['title'], 'content':'Approved version', 'status':'internal_only'}
        record[field] = wrong
        path.write_text(json.dumps([record]))
        before = path.read_bytes()
        with pytest.raises(HTTPException) as err:
            m.file_approved_deliverable(task['id'], req())
        assert err.value.status_code == 409
        assert path.read_bytes() == before
