"""Regression: PDS Moses must identify saved jobs for conversational estimate requests.

No customer records are modified and no estimate is created automatically.
"""
from types import SimpleNamespace
from app.routers import doorks_assistant as assistant


def _request():
    jobs = [
        {'id': 'pds-1', 'customer': 'The Irvine Company', 'job_number': '1126-03',
         'status': 'Quote', 'date': '2026-11-13', 'address': '123 Test Way'},
        {'id': 'pds-2', 'customer': 'The Irvine Company', 'job_number': '1126-01',
         'status': 'Dispatch', 'date': '2026-11-14'},
        {'id': 'pds-3', 'customer': 'Unrelated Company', 'job_number': '1126-04',
         'status': 'Quote', 'date': '2026-11-15'},
    ]
    class Store:
        def list_jobs(self):
            return jobs
    return SimpleNamespace(
        state=SimpleNamespace(auth_user='test', auth_role='office_admin'),
        session={'active_platform': 'pds'},
        app=SimpleNamespace(state=SimpleNamespace(calendar_store=Store(), data_dir='/tmp/no-data')),
    )


def test_conversational_pds_quote_request_locates_saved_customer_and_chooses_quote(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    response = assistant.chat(assistant.Message(message=(
        'Can you create an estimate from the most recent Irvine company job that needs quote?'
    )), _request())
    assert response['workspace'] == 'pds'
    assert response['matches'][0]['id'] == 'pds-1'
    assert all('Irvine' in entry['name'] for entry in response['matches'])
    assert 'no estimate was created' in response['answer'].lower()


def test_pds_quote_request_does_not_invent_missing_job(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    response = assistant.chat(assistant.Message(message=(
        'Create an estimate from the most recent Nonexistent customer job that needs quote'
    )), _request())
    assert response['matches'] == []
    assert 'could not verify' in response['answer']
