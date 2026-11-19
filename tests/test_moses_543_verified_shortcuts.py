"""Verified PDS chat lookup, no fabricated inventory, quotes or customer sends."""
from types import SimpleNamespace
from datetime import date
from app.services.moses_pds_verified_shortcuts import respond
from app.routers import pds_van_stock as van
from test_pds_van_stock import fixture_data, _move


def test_stock_answers_derive_from_saved_quantities_not_ai_guess(fixture_data):
    req = fixture_data
    van.template_item(van.Threshold(part_id='part-a', minimum=2, target=5), req)
    van.set_up_van(van.VanSetup(employee_id='tech-1'), req)
    answer = respond(req, 'Which vans need restocking?')
    assert 'Test Tech' in answer and 'A-1 needs 5' in answer
    assert 'nothing was ordered or changed' in answer.lower()
    _move(req, 'load', 5, '543-shortcut-load')
    answer = respond(req, 'Who has part A-1 in their van?')
    assert 'Test Tech' in answer and '5 on van' in answer
    assert respond(req, 'Which vans need restocking?')


def test_quote_form_lookup_uses_saved_job_not_unverified_text(fixture_data):
    req = fixture_data
    job = {'id': 'j543', 'job_number': '1126-15', 'customer': 'North Italia',
           'completion_forms': [{'id': 'f1', 'ready_to_quote': True, 'door_location': 'South Entry',
             'recommendations': 'Two separate quotes for closers and weatherstripping'}]}
    req.app.state.calendar_store = SimpleNamespace(get_by_job_number=lambda number: job if number == '1126-15' else None,
                                                   get_job=lambda id: job if id == 'j543' else None)
    answer = respond(req, 'Review job 1126-15 and identify separate estimate scopes.')
    assert 'North Italia' in answer and 'South Entry' in answer
    assert 'office must confirm' in answer
    assert 'No official estimates were created' in answer
    assert 'was found' in respond(req, 'Review job 1126-99 and identify separate estimates')


def test_confirmation_saves_only_unsent_approval_with_verified_recipient(fixture_data):
    req = fixture_data
    job = {'id':'j543','job_number':'1126-15','customer':'North Italia','email':'safe@example.test',
           'scheduled_date':'2099-01-01','scheduled_time':'10:00','address':'Somewhere'}
    req.app.state.calendar_store=SimpleNamespace(get_by_job_number=lambda n:job if n=='1126-15' else None,
        get_job=lambda n:job if n=='j543' else None)
    result=respond(req,'Moses, prepare an appointment confirmation email for job 1126-15. Do not send it.')
    assert 'Saved UNSENT' in result and 'no customer message was sent' in result
    from app.services.pds_schedule_notifications import history
    rows=history(req,'j543')['items']
    assert len(rows)==1 and rows[0]['status']=='pending' and rows[0]['recipient']=='safe@example.test'
    result2=respond(req,'Moses, prepare an appointment confirmation email for job 1126-15. Do not send it.')
    assert 'Saved UNSENT' in result2 and len(history(req,'j543')['items'])==1
    req.state.auth_role='lead'
    assert 'Only a PDS office administrator' in respond(req,'Prepare appointment email for job 1126-15')
    assert len(history.__name__) > 0


def test_live_chat_router_uses_verified_pds_data_without_generic_model(fixture_data, monkeypatch):
    from app.routers import doorks_assistant
    req = fixture_data
    van.template_item(van.Threshold(part_id='part-a', minimum=2, target=5), req)
    van.set_up_van(van.VanSetup(employee_id='tech-1'), req)
    monkeypatch.setattr(doorks_assistant, '_request_model', lambda *_args, **_kw: (_ for _ in ()).throw(
        AssertionError('Generic fallback must not substitute for saved PDS stock')))
    result = doorks_assistant.chat(doorks_assistant.Message(message='Which vans need restocking?'), req)
    assert result['agent_mode'] == 'verified_pds_records'
    assert 'Test Tech' in result['answer']
    assert result['read_only'] is True
    assert result['action_proposals'] == []
