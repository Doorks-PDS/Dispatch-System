"""PRIO Coin PDS admin simulation uses isolated, durable trial-only records."""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from app.routers.pds_prio_trials import router


def test_prio_trials_save_reload_and_permissions(tmp_path):
    app = FastAPI()
    app.state.data_dir = str(tmp_path)

    @app.middleware('http')
    async def fake_login(request: Request, call_next):
        request.state.auth_user = {'id': 'pds-test-admin'}
        request.state.auth_role = request.headers.get('x-role', 'office_admin')
        request.session['active_platform'] = request.headers.get('x-platform', 'pds')
        return await call_next(request)

    app.add_middleware(SessionMiddleware, secret_key='isolated-test')
    app.include_router(router)
    with TestClient(app) as client:
        assert client.get('/pds-prio-trials', headers={'x-role':'tech'}).status_code == 403
        assert client.get('/pds-prio-trials', headers={'x-platform':'sdc'}).status_code == 403
        assert client.get('/pds-prio-trials').json()['entries'] == []
        payload = {'date':'2026-11-18','amount':100.23,'frequency':'Quarterly','notes':'Trial only'}
        response = client.post('/pds-prio-trials',json=payload)
        assert response.status_code == 200, response.text
        assert response.json()['entry']['amount_cents'] == 10023
        entries = client.get('/pds-prio-trials').json()['entries']
        assert len(entries) == 1 and entries[0]['simulation_only']
        assert client.post('/pds-prio-trials',json=payload,headers={'x-role':'office'}).status_code == 403
        assert client.post('/pds-prio-trials',json=dict(payload,amount=-5)).status_code == 422
        assert not (tmp_path/'pds_prio_simulated_trials.json.tmp').exists()
        assert (tmp_path/'pds_prio_simulated_trials.json').exists()


def test_prio_invalid_stored_data_fail_closed(tmp_path):
    from app.routers.pds_prio_trials import _load
    from fastapi import HTTPException
    import pytest
    file = tmp_path/'pds_prio_simulated_trials.json'
    file.write_text('{bad')
    with pytest.raises(HTTPException) as error:
        _load(file)
    assert error.value.status_code == 503
