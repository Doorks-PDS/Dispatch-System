"""Moses uses existing PDS Scheduler approval backend, never sends by itself."""
import json
import sys
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_agent


def request(tmp_path, platform='pds', role='office_admin'):
    job = {'id': 'job-540', 'customer': 'Test Customer', 'email': 'test@example.com',
           'status': 'Scheduled', 'scheduled_date': '2026-11-19'}
    store = SimpleNamespace(get_job=lambda key: job if key == job['id'] else None)
    return SimpleNamespace(session={'active_platform': platform},
                           state=SimpleNamespace(auth_user={'id': 'office-1'}, auth_role=role),
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path), calendar_store=store)))


def tools_for(monkeypatch, request):
    seen = {}
    class Agent:
        def __init__(self, **kwargs): seen.update(kwargs)
    class Runner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            return SimpleNamespace(final_output='Prepared for review, not sent.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=Agent, Runner=Runner, RunConfig=lambda **kwargs: None, function_tool=lambda func: func))
    moses_agent.answer(request, 'Review customer messages', [])
    return {tool.__name__: tool for tool in seen['tools']}


def test_moses_scheduler_email_requires_approval_and_preserves_history(tmp_path, monkeypatch):
    req = request(tmp_path)
    tools = tools_for(monkeypatch, req)
    prepare = tools['prepare_pds_schedule_email']
    history = tools['get_pds_schedule_email_history']
    args = ('job-540', 'test@example.com', 'appointment', 'Confirm your appointment',
            'Priority Door Systems: Your appointment is scheduled for tomorrow.')
    first = json.loads(prepare(*args))
    assert first['status'] == 'pending' and first['approval_required'] and first['sent'] is False
    second = json.loads(prepare(*args))
    assert first['proposal_id'] == second['proposal_id'] and second['reused_pending']
    rows = json.loads(history('job-540'))['notifications']
    assert len(rows) == 1 and rows[0]['status'] == 'pending'
    assert rows[0]['provider_submitted'] is False
    assert 'test@example.com' not in json.dumps(rows)
    assert 'Your appointment is scheduled' not in json.dumps(rows)


def test_moses_scheduler_email_rejects_unverified_recipient_and_wrong_job(tmp_path, monkeypatch):
    req = request(tmp_path)
    tools = tools_for(monkeypatch, req)
    with pytest.raises(HTTPException) as failure:
        tools['prepare_pds_schedule_email']('job-540', 'attacker@example.com', 'appointment',
                                            'Subject', 'Priority Door Systems: Schedule confirmed.')
    assert failure.value.status_code == 409
    with pytest.raises(HTTPException) as failure:
        tools['get_pds_schedule_email_history']('unknown-job')
    assert failure.value.status_code == 404


def test_moses_scheduler_email_only_registered_in_pds(tmp_path, monkeypatch):
    for platform in ('doorks', 'sdc'):
        tools = tools_for(monkeypatch, request(tmp_path, platform=platform))
        assert 'prepare_pds_schedule_email' not in tools
        assert 'get_pds_schedule_email_history' not in tools
