"""Completion form deductions bind exact saved source and stay idempotent."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import pds_van_stock as v
from test_pds_van_stock import fixture_data, _move


def _setup(r):
    r.app.state.calendar_store=SimpleNamespace(get_job=lambda job_id:
        {'id':'job-1','job_number':'1126-15', 'completion_forms':[
            {'id':'form-1','technician_name':'Test Tech','parts_used':'Van stock used: 2 × Test closer [part-a]'}]} if job_id=='job-1' else None)
    v.set_up_van(v.VanSetup(employee_id='tech-1'), r)
    _move(r,'load',5,'stock-loaded-542')


def test_form_usage_deducts_once_without_second_warehouse_deduction(fixture_data):
    r=fixture_data;_setup(r)
    payload=v.CompletionUsage(job_id='job-1',form_id='form-1',employee_id='tech-1',part_id='part-a',quantity=2)
    first=v.completion_usage(payload,r)
    assert first['van_quantity']==3 and not first['duplicate']
    assert v.completion_usage(payload,r)['duplicate']
    state=v.overview(r)
    assert state['vans'][0]['items'][0]['quantity']==3
    assert next(p for p in state['catalog'] if p['id']=='part-a')['warehouse']==5
    with pytest.raises(HTTPException) as err:
        v.completion_usage(payload.model_copy(update={'quantity':3}),r)
    assert err.value.status_code==409


def test_completion_usage_requires_matching_saved_form_and_technician(fixture_data):
    r=fixture_data;_setup(r)
    base=dict(job_id='job-1',form_id='form-1',employee_id='tech-1',part_id='part-a',quantity=1)
    for change in [{'form_id':'no-form'},{'job_id':'unknown'}]:
        with pytest.raises(HTTPException) as err:
            v.completion_usage(v.CompletionUsage(**(base|change)),r)
        assert err.value.status_code==404
    r.app.state.calendar_store=SimpleNamespace(get_job=lambda _:{'job_number':'1126-15','completion_forms':[{'id':'form-1','technician_name':'Other Tech'}]})
    with pytest.raises(HTTPException) as err:
        v.completion_usage(v.CompletionUsage(**base),r)
    assert err.value.status_code==409


def test_technician_can_only_report_own_saved_van_usage(fixture_data):
    r=fixture_data;_setup(r)
    r.app.state.calendar_store=SimpleNamespace(get_job=lambda job_id:{'job_number':'1126-15', 'completion_forms':[{'id':'form-1','technician_name':'Test Tech','parts_used':'Van stock used: 1 × Test closer [part-a]'}]})
    r.state.auth_role='tech';r.state.auth_user={'name':'Test Tech'}
    item=v.CompletionUsage(job_id='job-1',form_id='form-1',employee_id='tech-1',part_id='part-a',quantity=1)
    assert v.completion_usage(item,r)['ok']
    r.state.auth_user={'name':'Other Tech'}
    with pytest.raises(HTTPException) as err:v.completion_usage(item,r)
    assert err.value.status_code==403
    with pytest.raises(HTTPException) as err:
        _move(r,'load',1,'tech-manual-load-542')
    assert err.value.status_code==403


def test_standard_template_does_not_change_existing_vans(fixture_data):
    r=fixture_data
    v.set_up_van(v.VanSetup(employee_id='tech-1'),r)
    v.template_item(v.Threshold(part_id='part-a',minimum=2,target=5),r)
    current=v.overview(r)
    assert current['template']['part-a']=={'minimum':2,'target':5}
    assert current['vans'][0]['items']==[]
    v.set_up_van(v.VanSetup(employee_id='tech-1',enabled=False),r)
    v.set_up_van(v.VanSetup(employee_id='tech-1',enabled=True),r)
    assert v.overview(r)['vans'][0]['items']==[]


def test_atomic_transfer_between_vans_preserves_warehouse(fixture_data, monkeypatch):
    r=fixture_data
    monkeypatch.setattr(v, '_people', lambda _: {
        'tech-1':{'id':'tech-1','name':'Test Tech','role':'tech'},
        'tech-2':{'id':'tech-2','name':'Second Tech','role':'lead'}})
    v.set_up_van(v.VanSetup(employee_id='tech-1'),r)
    v.set_up_van(v.VanSetup(employee_id='tech-2'),r)
    _move(r,'load',5,'load-pair-542')
    req=v.VanTransfer(from_employee_id='tech-1',to_employee_id='tech-2',part_id='part-a',quantity=2,
                      reason='Service stock transfer',request_id='pair-transfer-542')
    assert v.van_to_van(req,r)['duplicate'] is False
    assert v.van_to_van(req,r)['duplicate'] is True
    view=v.overview(r)
    counts={i['employee_id']:i['items'][0]['quantity'] for i in view['vans']}
    assert counts=={'tech-1':3,'tech-2':2}
    assert next(p for p in view['catalog'] if p['id']=='part-a')['warehouse']==5
    with pytest.raises(HTTPException) as err:v.van_to_van(req.model_copy(update={'quantity':3}),r)
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:v.van_to_van(req.model_copy(update={'quantity':9,'request_id':'pair-too-much'}),r)
    assert err.value.status_code==409
