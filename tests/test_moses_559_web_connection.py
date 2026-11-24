"""Moses 5.59: hosted web verification is proof-based and admin-only."""
from types import SimpleNamespace
from pathlib import Path
import sys
import pytest
from fastapi import HTTPException

from app.services import moses_web_probe, moses_agent
from app.routers import doorks_assistant

def request(platform='pds', role='office_admin', header='hosted-web-check'):
    return SimpleNamespace(session={'active_platform':platform},
                           state=SimpleNamespace(auth_user='office', auth_role=role),
                           headers={'x-moses-validation':header})

def test_web_proof_requires_actual_provider_call():
    assert not moses_web_probe._web_search_called(SimpleNamespace(final_output='I searched the web'))
    assert not moses_web_probe._web_search_called(SimpleNamespace(raw_responses=[
        SimpleNamespace(output=[{'type':'web_search_call','status':'failed'}])]))
    assert moses_web_probe._web_search_called(SimpleNamespace(raw_responses=[
        SimpleNamespace(output=[SimpleNamespace(type='web_search_call')])]))
    assert moses_web_probe._web_search_called(SimpleNamespace(raw_responses=[
        SimpleNamespace(output=[{'type':'web_search_call'}])]))

def test_web_check_requires_admin_and_explicit_header(monkeypatch):
    monkeypatch.setattr(moses_web_probe, 'check', lambda p: {'workspace':p,'result':'test'})
    assert doorks_assistant.agent_web_check(request())['workspace']=='pds'
    with pytest.raises(HTTPException) as exc:
        doorks_assistant.agent_web_check(request(role='technician'))
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        doorks_assistant.agent_web_check(request(header=''))
    assert exc.value.status_code==400

def test_probe_uses_no_provider_without_readiness(monkeypatch):
    monkeypatch.setattr(moses_agent,'readiness',lambda _p:{'ready_for_live_check':False,
      'internet_research_requested':False,'web_live_test_enabled':False})
    assert moses_web_probe.check('pds')['result']=='agent_not_configured'
    monkeypatch.setattr(moses_agent,'readiness',lambda _p:{'ready_for_live_check':True,
      'internet_research_requested':False,'web_live_test_enabled':False})
    assert moses_web_probe.check('pds')['result']=='web_search_disabled'
    monkeypatch.setattr(moses_agent,'readiness',lambda _p:{'ready_for_live_check':True,
      'internet_research_requested':True,'web_live_test_enabled':False})
    assert moses_web_probe.check('pds')['result']=='live_test_not_enabled'

def test_probe_can_confirm_hosted_web_tool_without_business_tool(monkeypatch):
    monkeypatch.setattr(moses_agent,'readiness',lambda _p:{'ready_for_live_check':True,
      'internet_research_requested':True,'web_live_test_enabled':True})
    calls=[]
    class FakeAgent:
        def __init__(self,**kwargs):
            assert len(kwargs['tools'])==1
            assert kwargs['name'].startswith('Moses public web-search')
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            calls.append(turns)
            return SimpleNamespace(final_output='Official page',raw_responses=[
                SimpleNamespace(output=[SimpleNamespace(type='web_search_call')])])
    monkeypatch.setitem(sys.modules,'agents',SimpleNamespace(Agent=FakeAgent,Runner=FakeRunner,
                        RunConfig=lambda **kw:None,WebSearchTool=lambda **kw:'web'))
    result=moses_web_probe.check('pds')
    assert result['web_search_verified'] is True
    assert result['business_record_access_verified'] is False
    assert result['result']=='hosted_web_search_verified'
    assert 'OpenAI API web search documentation' in str(calls)

def test_full_agent_prefers_live_sdk_over_legacy_shortcuts(monkeypatch):
    # Do not allow PDS keyword shortcuts to preempt a configured office-admin agent.
    src=(Path(__file__).resolve().parents[1]/'app/routers/doorks_assistant.py').read_text()
    assert 'if not live_admin:' in src
    assert 'verified_read_only' in src
    assert 'if may_retry_read_only(exc, request)' in src
    assert 'agent_web_check' in src

def test_readiness_never_claims_web_verified_from_flags(monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_WEB_SEARCH_ENABLED','true')
    monkeypatch.setenv('MOSES_LIVE_VALIDATION_ENABLED','true')
    out=moses_agent.readiness('pds')
    assert out['internet_research_requested'] is True
    assert out['internet_research_verified'] is False
    assert out['web_live_test_enabled'] is True
