"""Revision 57: multi-platform launch boundaries and PDS read-only tools."""
from types import SimpleNamespace
import sys
import pytest
from fastapi import HTTPException
from app.routers import doorks_assistant as assistant
from app.services import moses_agent


def req(platform='pds', role='office_admin'):
    jobs = [
        {'id': 'pds-1', 'job_number': '1126-11', 'customer': 'Acme', 'status': 'Scheduled',
         'address': '1 Main', 'date': '2026-11-15', 'private_token': 'SECRET'},
        {'id': 'pds-2', 'job_number': '1126-12', 'customer': 'Other', 'status': 'Complete'},
    ]
    store = SimpleNamespace(list_jobs=lambda: jobs, get_job=lambda identifier: next((x for x in jobs if x['id'] == identifier), None))
    return SimpleNamespace(state=SimpleNamespace(auth_user='admin', auth_role=role),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(calendar_store=store)))


def test_flags_are_isolated_and_fail_closed(monkeypatch):
    for key in ('DOORKS_SDC_AGENT_ENABLED', 'DOORKS_MOSES_DOORKS_AGENT_ENABLED', 'DOORKS_MOSES_PDS_AGENT_ENABLED'):
        monkeypatch.delenv(key, raising=False)
    assert not any(moses_agent.enabled(p) for p in ('sdc', 'doorks', 'pds', 'unknown'))
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED', 'true')
    assert moses_agent.enabled('pds') and not moses_agent.enabled('sdc') and not moses_agent.enabled('doorks')


def test_pds_search_is_bounded_and_only_pds(monkeypatch):
    result = assistant._execute_pds_tool(req(), 'search_pds_jobs', {'query': 'Acme'})
    assert result['matching_count'] == 1 and result['examples'][0]['id'] == 'pds-1'
    assert 'private_token' not in str(result)
    assert result['read_only']
    assert assistant._execute_pds_tool(req(), 'update_job', {'id': 'pds-1'})['error'] == 'Tool is not authorized'
    for p, role in [('sdc', 'office_admin'), ('doorks', 'office_admin'), ('pds', 'technician')]:
        with pytest.raises(HTTPException) as err:
            assistant._execute_pds_tool(req(p, role), 'search_pds_jobs', {'query': 'Acme'})
        assert err.value.status_code == 403


def test_pds_agent_has_search_and_proposal_only(monkeypatch):
    captured = {}
    class FakeAgent:
        def __init__(self, **kwargs): captured.update(kwargs)
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            return SimpleNamespace(final_output='Found your job; no changes made.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=FakeAgent, Runner=FakeRunner, RunConfig=lambda **kwargs: None,
        function_tool=lambda fn: fn))
    assert 'no changes' in moses_agent.answer(req(), 'Find Acme', []).lower()
    assert [tool.__name__ for tool in captured['tools']] == [
        'get_moses_permissions', 'prepare_moses_action', 'get_moses_action_receipt',
        'get_moses_pending_actions', 'get_moses_action_center', 'get_business_briefing',
        'review_purchase_order_receiving', 'propose_purchase_order_receipt',
        'search_pds_jobs', 'get_pds_job_details', 'get_pds_work_queue',
        'get_verified_pds_draft', 'get_verified_pds_job_context', 'prepare_pds_job_quote_review',
        'review_pds_document_delivery', 'prepare_pds_document_delivery',
        'get_pending_pds_document_emails', 'prepare_customer_dispatch_update',
        'get_pds_estimate_context', 'get_pds_estimate_preview', 'propose_pds_job_status',
        'inspect_product_page', 'propose_pds_catalog_part', 'preview_dispatch_customer_email',
        'propose_vendor_po_email'
    ]
    assert all('delete' not in tool.__name__ and 'send' not in tool.__name__ for tool in captured['tools'])
    assert 'PDS' in captured['name']
    with pytest.raises(HTTPException):
        moses_agent.answer(req('sdc', 'technician'), 'Find Acme', [])


def test_readiness_scoped_to_selected_platform(monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED', 'true')
    assert assistant.agent_readiness(req())['workspace'] == 'pds'
    with pytest.raises(HTTPException):
        assistant.agent_readiness(req('pds', 'technician'))


def test_pds_agent_route_selected_only_with_flag(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake')
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED', 'true')
    monkeypatch.setattr(moses_agent, 'answer', lambda *_: 'PDS-only response')
    result = assistant.chat(assistant.Message(message='find Acme'), req())
    assert result['workspace'] == 'pds' and result['answer'] == 'PDS-only response'
