"""PDS week-ready Moses: bounded job cards and safely prepared estimate handoff."""
from types import SimpleNamespace
from app.routers import doorks_assistant as assistant


def request():
    jobs=[
        {'id':'wk-q1','job_number':'1126-14','customer':'Fixture Service Co','status':'To Be Quoted','date':'2026-11-16','completion_forms':[{'ready_to_quote':True,'recommendations':'Replace worn latch'}]},
        {'id':'wk-n1','job_number':'1126-15','customer':'Fixture Office','status':'Scheduled','date':'2026-11-17'},
        {'id':'wk-done','job_number':'1126-16','customer':'Fixture Complete','status':'Complete','date':'2026-11-17'},
    ]
    class Store:
        def list_jobs(self): return jobs
        def get_job(self, ident): return next((r for r in jobs if r['id']==ident),None)
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'},auth_role='office_admin'),
        session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(calendar_store=Store())))


def test_open_jobs_are_structured_and_closed_excluded(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    reply=assistant.chat(assistant.Message(message='Show open jobs'),request())
    assert reply['queue_cards'][0]['group']=='open_jobs'
    assert reply['queue_cards'][0]['count']==2
    assert {r['id'] for r in reply['queue_cards'][0]['jobs']}=={'wk-q1','wk-n1'}
    assert 'wk-done' not in str(reply)


def test_quote_handoff_never_saves_or_numbers(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    reply=assistant.chat(assistant.Message(message='Prepare an estimate for Fixture Service Co job'),request())
    assert reply['matches'][0]['id']=='wk-q1'
    assert reply['matches'][0]['can_prepare_estimate'] is True
    assert 'No estimate was created' in reply['answer']
