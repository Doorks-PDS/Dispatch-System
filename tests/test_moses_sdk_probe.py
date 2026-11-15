"""Offline contract tests: actual provider calls are never made in this suite."""
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import moses_sdk_probe
from app.routers import doorks_assistant


def test_probe_refuses_unconfigured_agent(monkeypatch):
    monkeypatch.setattr('app.services.moses_agent.readiness', lambda _p: {'ready_for_live_check': False})
    result = moses_sdk_probe.check('pds')
    assert result['result'] == 'not_configured'
    assert result['deployment_authorized'] is False
    assert result['sdk_tool_execution_verified'] is False


def test_probe_requires_separate_explicit_test_switch(monkeypatch):
    monkeypatch.setattr('app.services.moses_agent.readiness', lambda _p: {'ready_for_live_check': True})
    monkeypatch.delenv('MOSES_LIVE_VALIDATION_ENABLED', raising=False)
    assert moses_sdk_probe.check('doorks')['result'] == 'live_test_not_enabled'


def test_probe_validates_real_agents_tool_execution_contract(monkeypatch):
    monkeypatch.setattr('app.services.moses_agent.readiness', lambda _p: {'ready_for_live_check': True})
    monkeypatch.setenv('MOSES_LIVE_VALIDATION_ENABLED', 'true')
    captured = {}

    def function_tool(fn):
        captured['fn'] = fn
        return fn

    class Agent:
        def __init__(self, **kwargs):
            captured['tools'] = kwargs['tools']

    class Runner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            token = turns[0]['content'].split('challenge_token=')[1]
            assert captured['tools'][0](token) == 'MOSES_SYNTHETIC_TOOL_OK'
            return SimpleNamespace(final_output='Synthetic tool finished')

    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=Agent, Runner=Runner, RunConfig=lambda **_kwargs: None,
        function_tool=function_tool))
    result = moses_sdk_probe.check('sdc')
    assert result['result'] == 'synthetic_tool_verified'
    assert result['sdk_tool_execution_verified'] is True
    assert result['record_access_verified'] is False
    assert result['approval_execution_verified'] is False
    assert result['deployment_authorized'] is False


def test_probe_failure_is_safe_and_does_not_claim_success(monkeypatch):
    monkeypatch.setattr('app.services.moses_agent.readiness', lambda _p: {'ready_for_live_check': True})
    monkeypatch.setenv('MOSES_LIVE_VALIDATION_ENABLED', 'true')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=lambda **kwargs: None,
        Runner=SimpleNamespace(run_sync=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('secret-do-not-echo'))),
        RunConfig=lambda **kwargs: None,
        function_tool=lambda f: f))
    result = moses_sdk_probe.check('pds')
    assert result['result'] == 'provider_or_sdk_call_failed'
    assert 'secret-do-not-echo' not in str(result)


def test_endpoint_enforces_session_and_admin(monkeypatch):
    req = SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'staff'}, auth_role='technician'),
                          session={'active_platform': 'pds'},
                          headers={'x-moses-validation': 'synthetic-tool-check'})
    with pytest.raises(HTTPException) as error:
        doorks_assistant.agent_sdk_tool_check(req)
    assert error.value.status_code == 403
    req.state.auth_role = 'office_admin'
    req.headers = {}
    with pytest.raises(HTTPException) as error:
        doorks_assistant.agent_sdk_tool_check(req)
    assert error.value.status_code == 400
    req.headers = {'x-moses-validation': 'synthetic-tool-check'}
    monkeypatch.setattr(moses_sdk_probe, 'check', lambda p: {'workspace': p, 'deployment_authorized': False})
    assert doorks_assistant.agent_sdk_tool_check(req)['workspace'] == 'pds'
