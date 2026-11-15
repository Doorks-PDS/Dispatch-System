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


def test_pds_estimate_context_is_bounded_and_admin_only():
    req, store = make_request()
    # General detail stays private, but a requested quote has bounded technician scope.
    store.jobs['p-1']['completion_forms'] = [
        {'tech_notes': 'Replace failed closer', 'parts_used': '1 closer',
         'private_token': 'SECRET_FORM_DATA'}]
    context = _execute_pds_tool(req, 'get_pds_estimate_context', {'record_id': 'p-1'})
    assert context['verified'] and context['read_only']
    assert context['draft_created'] is False
    assert 'Replace failed closer' in str(context)
    assert 'SECRET_FORM_DATA' not in str(context)
    assert 'PRIVATE_INTERNAL_NOTES' not in str(context)
    assert store.calls >= 1
    req, _ = make_request(role='technician')
    with pytest.raises(HTTPException) as err:
        _execute_pds_tool(req, 'get_pds_estimate_context', {'record_id': 'p-1'})
    assert err.value.status_code == 403


def test_work_queue_is_admin_only_and_counts_full_store():
    req, store = make_request()
    store.jobs['p-2'] = {'id':'p-2','customer':'Synthetic Client','status':'To Be Quoted'}
    store.jobs['p-3'] = {'id':'p-3','customer':'Synthetic Client','status':'To Be Quoted'}
    summary = _execute_pds_tool(req, 'get_pds_work_queue')
    assert summary['read_only']
    assert summary['total_saved_jobs'] == 3
    assert summary['queues']['needs_quote']['count'] == 2
    assert len(summary['queues']['needs_quote']['examples']) == 2
    assert 'PRIVATE_INTERNAL_NOTES' not in str(summary)
    assert 'SECRET_PRIVATE' not in str(summary)
    req, _ = make_request(role='technician')
    with pytest.raises(HTTPException) as err:
        _execute_pds_tool(req, 'get_pds_work_queue')
    assert err.value.status_code == 403


def test_moses_pds_queue_question_uses_saved_records(monkeypatch):
    from app.routers import doorks_assistant as assistant
    from types import SimpleNamespace
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    jobs = [
        {'id': 'q1', 'customer': 'Synthetic Customer', 'job_number': '1126-01', 'status': 'To Be Quoted', 'private_token': 'SECRET'},
        {'id': 'q2', 'customer': 'Synthetic Customer', 'job_number': '1126-02', 'status': 'To Be Invoiced'},
    ]
    r = SimpleNamespace(state=SimpleNamespace(auth_user='test', auth_role='office_admin'),
         session={'active_platform': 'pds'},
         app=SimpleNamespace(state=SimpleNamespace(calendar_store=SimpleNamespace(list_jobs=lambda:jobs))))
    quote = assistant.chat(assistant.Message(message='Show me what needs quoting'), r)
    assert 'Needs quote: 1' in quote['answer']
    assert quote['matches'][0]['id'] == 'q1'
    assert 'SECRET' not in str(quote)
    invoice = assistant.chat(assistant.Message(message='What needs invoicing?'), r)
    assert 'Needs invoice: 1' in invoice['answer']
    assert invoice['matches'][0]['id'] == 'q2'


def test_agent_disabled_never_uses_ungrounded_chat_model(monkeypatch):
    from app.routers import doorks_assistant as assistant
    from types import SimpleNamespace
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-key-no-network')
    monkeypatch.delenv('DOORKS_MOSES_PDS_AGENT_ENABLED', raising=False)
    monkeypatch.setattr(assistant, '_request_model', lambda *_: (_ for _ in ()).throw(AssertionError('Generic model must not be called')))
    r = SimpleNamespace(state=SimpleNamespace(auth_user='test', auth_role='office_admin'),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(calendar_store=SimpleNamespace(list_jobs=lambda:[]))))
    result = assistant.chat(assistant.Message(message='What can you do with our business?'), r)
    assert result['agent_connected'] is False
    assert 'not enabled' in result['answer']


def test_moses_estimate_preview_uses_existing_description_builder(monkeypatch):
    req, store = make_request()
    store.jobs['p-1']['completion_forms'] = [{
        'ready_to_quote': True,
        'recommendations': 'Replace defective closer and adjust door',
        'parts_used': 'Previously installed hardware',
        'private_token': 'DO_NOT_SEND_PRIVATE'}]
    from app.routers import documents
    called = []
    def fake_builder(payload):
        called.append(payload)
        return 'Proposal Includes - replace defective closer and adjust door'
    monkeypatch.setattr(documents, 'generate_description_from_data', fake_builder)
    preview = _execute_pds_tool(req, 'get_pds_estimate_preview', {'record_id': 'p-1'})
    assert preview['verified'] and preview['read_only']
    assert preview['draft_saved'] is False
    assert preview['official_number_assigned'] is False
    assert 'replace defective closer' in preview['description_preview']
    assert called[0]['doc_type'] == 'estimate'
    assert 'DO_NOT_SEND_PRIVATE' not in str(preview)
    assert 'DO_NOT_SEND_PRIVATE' not in str(called)
    assert 'PRIVATE_INTERNAL_NOTES' not in str(preview)
    req, _ = make_request(role='technician')
    with pytest.raises(HTTPException) as err:
        _execute_pds_tool(req, 'get_pds_estimate_preview', {'record_id': 'p-1'})
    assert err.value.status_code == 403


def test_moses_estimate_preview_fails_closed_for_unknown_job():
    req, _ = make_request()
    result = _execute_pds_tool(req, 'get_pds_estimate_preview', {'record_id': 'invalid-id'})
    assert result['verified'] is False
    assert 'description_preview' not in result
