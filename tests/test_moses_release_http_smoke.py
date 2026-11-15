"""HTTP-boundary smoke checks for the cumulative Moses release.

Runs with temporary state and no provider calls, production secrets, or sends.
"""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.routers.doorks_assistant import router as moses_router


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    for name in (
        'OPENAI_API_KEY', 'DOORKS_SDC_AGENT_ENABLED',
        'DOORKS_MOSES_DOORKS_AGENT_ENABLED', 'DOORKS_MOSES_PDS_AGENT_ENABLED',
    ):
        monkeypatch.delenv(name, raising=False)

    def make(platform='pds', role='office_admin'):
        app = FastAPI()
        app.state.data_dir = str(tmp_path)
        app.state.calendar_store = SimpleNamespace(list_jobs=lambda: [])

        @app.middleware('http')
        async def mocked_authenticated_session(request: Request, call_next):
            request.state.auth_user = {'id': 'test-office'}
            request.state.auth_role = role
            request.session['active_platform'] = platform
            return await call_next(request)

        app.add_middleware(SessionMiddleware, secret_key='test-only-not-a-production-key')
        app.include_router(moses_router)
        return TestClient(app)

    return make


@pytest.mark.parametrize('platform', ['pds', 'doorks', 'sdc'])
def test_agent_readiness_http_is_scoped_and_no_secrets(client_factory, platform):
    response = client_factory(platform).get('/doorks-assistant/agent-readiness')
    assert response.status_code == 200
    body = response.json()
    assert body['workspace'] == platform
    assert body['agent_enabled'] is False
    assert body['api_key_configured'] is False
    assert body['live_api_verified'] is False
    assert 'key' not in str(body).lower().replace('api_key_configured', '')


def test_agent_readiness_blocks_non_office_user(client_factory):
    response = client_factory('pds', 'technician').get('/doorks-assistant/agent-readiness')
    assert response.status_code == 403


def test_chat_with_no_ai_key_is_read_only_and_returns_workspace(client_factory, tmp_path):
    response = client_factory('pds').post('/doorks-assistant/chat', json={'message': 'Find job 999'})
    assert response.status_code == 200
    assert response.json()['workspace'] == 'pds'
    assert list(tmp_path.rglob('*.json')) == []


def test_storage_readiness_http_reports_expected_mount_without_writes(client_factory, tmp_path, monkeypatch):
    mount = tmp_path / 'persistent'
    monkeypatch.setenv('MOSES_EXPECTED_RENDER_DISK_MOUNT', str(mount))
    response = client_factory('pds').get('/doorks-assistant/storage-readiness')
    assert response.status_code == 200
    body = response.json()
    assert body['disk_path_mismatch'] is True
    assert body['configured_path_under_expected_disk'] is False
    assert not mount.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('platform', ['pds', 'doorks', 'sdc'])
def test_release_gate_http_never_authorizes_or_writes(client_factory, tmp_path, platform):
    response = client_factory(platform).get('/doorks-assistant/release-readiness')
    assert response.status_code == 200
    body = response.json()
    assert body['deployment_authorized'] is False
    assert body['production_end_to_end_verified'] is False
    assert set(body['agents']) == {'pds', 'doorks', 'sdc'}
    assert not list(tmp_path.rglob('*.json'))


def test_release_gate_http_blocks_technician(client_factory):
    response = client_factory('pds', 'technician').get('/doorks-assistant/release-readiness')
    assert response.status_code == 403
