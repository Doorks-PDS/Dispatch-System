# Regression: quote wording and workspace-scoped sender.
from types import SimpleNamespace
from app.routers import doorks_assistant
from app.services import moses_mail_identity

def _request():
    jobs = [
        {'id': 'test-bay-1', 'customer': 'Bay City Electric Works', 'job_number': '1026-77', 'status': 'Complete/Quote', 'date': '2026-11-14', 'completion_forms': [{'additional_recommendations': 'Replace worn closer.'}]},
        {'id': 'unrelated', 'customer': 'Other Customer', 'job_number': '1026-78', 'status': 'Quote', 'date': '2026-11-15'}]
    class Store:
        def list_jobs(self): return jobs
        def get_job(self, ident): return next((row for row in jobs if row['id'] == ident), None)
    return SimpleNamespace(state=SimpleNamespace(auth_user='test', auth_role='office_admin'), session={'active_platform':'pds'}, app=SimpleNamespace(state=SimpleNamespace(calendar_store=Store(), data_dir='/tmp/nonexistent')))

def test_bay_city_recommended_repairs_does_not_require_live_ai(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','dummy')
    from app.services import moses_agent
    monkeypatch.setattr(moses_agent,'answer',lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError('Should not use AI for a verified quote lookup')))
    response=doorks_assistant.chat(doorks_assistant.Message(message='can you give me a quote for the recommended repairs from Bay city electric works'),_request())
    assert response['matches'][0]['id']=='test-bay-1'
    assert 'Replace worn closer.' in response['answer']
    assert 'No estimate was created' in response['answer']
    assert all(m['name']=='Bay City Electric Works' for m in response['matches'])

def test_one_resend_sender_for_all_workspaces(monkeypatch):
    monkeypatch.setenv('MOSES_PDS_FROM','do-not-use@example.com')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    assert moses_mail_identity.identity('pds','estimate')['from']=='NoReply@prioritydoors.com'
    assert moses_mail_identity.identity('pds','estimate')['reply_to']=='Estimates@prioritydoors.com'
    assert moses_mail_identity.identity('sdc','estimate')['from']=='NoReply@prioritydoors.com'
    assert moses_mail_identity.identity('doorks','estimate')['from']=='NoReply@prioritydoors.com'
