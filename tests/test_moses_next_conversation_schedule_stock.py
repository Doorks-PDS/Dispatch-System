"""Nov 16 cumulative: agent-first chat, optional PDS scheduling, and audited stock."""
from __future__ import annotations
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.routers import doorks_assistant as assistant, pds_scheduling as scheduling, data
from app.services import moses_agent


def req(tmp_path, role='office_admin', platform='pds'):
    job={'id':'j-1','date':'2026-11-10','status':'Dispatch','source':'CURRENT','assigned_employee_ids':[]}
    class Store:
        def get_job(self, key): return dict(job) if key == 'j-1' else None
        def update_job(self, key, changes):
            if key!='j-1': return None
            job.update(changes)
            return dict(job)
    state=SimpleNamespace(auth_user={'id':'admin','name':'Office User'},auth_role=role,
             data_dir=tmp_path,project_root=tmp_path,
             employees_store=SimpleNamespace(list=lambda:[
              {'id':'a1','name':'Alice','role':'tech','active':True},
              {'id':'z1','name':'Zach','role':'lead','active':True}]),
             calendar_store=Store(),require_key=lambda *_:'office_admin')
    request=SimpleNamespace(state=state,app=SimpleNamespace(state=state),session={'active_platform':platform})
    return request,job


def test_live_agent_is_first_for_ordinary_quote_request(monkeypatch,tmp_path):
    request,_=req(tmp_path)
    monkeypatch.setattr(moses_agent,'readiness',lambda platform: {'ready_for_live_check':True})
    received={}
    def answer(request,message,history):
        received.update(message=message,history=history)
        request.state.moses_action_proposals=[]
        request.state.moses_document_proposals=[]
        return 'I checked the quote jobs and can prepare review drafts.'
    monkeypatch.setattr(moses_agent,'answer',answer)
    response=assistant.chat(assistant.Message(message='What jobs need to be quoted?',history=[{'role':'user','content':'PDS quotes'}]),request)
    assert response['agent_connected'] is True
    assert 'checked the quote jobs' in response['answer']
    assert 'queue_cards' not in response
    assert received['history']==[{'role':'user','content':'PDS quotes'}]


def test_global_agent_flag_and_workspace_override(monkeypatch):
    monkeypatch.setenv('DOORKS_MOSES_AGENT_ENABLED','true')
    for name in ('DOORKS_SDC_AGENT_ENABLED','DOORKS_MOSES_DOORKS_AGENT_ENABLED','DOORKS_MOSES_PDS_AGENT_ENABLED'):
        monkeypatch.delenv(name,raising=False)
    assert all(moses_agent.enabled(platform) for platform in ('pds','doorks','sdc'))
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED','false')
    assert not moses_agent.enabled('pds')
    assert moses_agent.enabled('doorks')


def test_visit_plan_optional_does_not_rewrite_dispatch_date_or_assignment(tmp_path):
    request,job=req(tmp_path)
    result=scheduling.visit_plan('j-1', scheduling.VisitPlan(employee_id='a1',scheduled_date='2026-11-20',scheduled_time='09:15'),request)
    assert result['ok'] and not result['updated_to_schedule']
    assert job['date']=='2026-11-10' and job['status']=='Dispatch'
    assert job['assigned_employee_ids']==[]
    assert job['planned_employee_id']=='a1'
    result=scheduling.visit_plan('j-1', scheduling.VisitPlan(employee_id='a1',scheduled_date='2026-11-20',scheduled_time='09:15',update_to_schedule=True),request)
    assert result['assignment_confirmed']
    assert job['date']=='2026-11-20' and job['status']=='Scheduled'
    assert job['assigned_employee_ids']==['a1']
    assert job['scheduled_time']=='09:15'


def test_visit_plan_optional_blank_is_allowed_but_invalid_schedule_blocks(tmp_path):
    request,job=req(tmp_path)
    assert scheduling.visit_plan('j-1',scheduling.VisitPlan(),request)['ok']
    with pytest.raises(HTTPException) as err:
        scheduling.visit_plan('j-1',scheduling.VisitPlan(update_to_schedule=True),request)
    assert err.value.status_code==422
    with pytest.raises(HTTPException):
        scheduling.visit_plan('j-1',scheduling.VisitPlan(scheduled_time='25:99'),request)
    assert job['date']=='2026-11-10'
    request.state.auth_role='tech'
    with pytest.raises(HTTPException) as err:
        scheduling.visit_plan('j-1',scheduling.VisitPlan(employee_id='a1'),request)
    assert err.value.status_code==403


def test_pds_part_stock_adjustments_preserve_master_and_audit(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'_parts_path',lambda request:tmp_path/'parts_catalog.json')
    request,_=req(tmp_path)
    part=data.create_part(request,data.PartPayload(part_number='311S',description='Closer',price=305,supplier_rate='175'),None)['item']
    assert part['price']==305 and part['supplier_rate']=='175'
    rows=data.list_parts(request,None)['items']
    assert rows[0]['stock_on_hand'] is None and rows[0]['stock_recorded'] is False
    result=data.adjust_pds_part_stock(part['id'],data.PdsStockAdjustment(delta=3,reason='Initial counted stock'),request)
    assert result['stock_on_hand']==3 and result['verified']
    result=data.adjust_pds_part_stock(part['id'],data.PdsStockAdjustment(delta=-1,reason='Used on job'),request)
    assert result['stock_on_hand']==2
    assert data.list_parts(request,None)['items'][0]['Price']==305
    assert data.list_parts(request,None)['items'][0]['stock_on_hand']==2
    with pytest.raises(HTTPException) as err:
        data.adjust_pds_part_stock(part['id'],data.PdsStockAdjustment(delta=-3,reason='Invalid negative stock'),request)
    assert err.value.status_code==409
    assert len(json.loads((tmp_path/'pds_parts_stock_events.json').read_text()))==2
    with pytest.raises(HTTPException) as err:
        data.delete_part(request,part['id'],None)
    assert err.value.status_code==409
    request.state.auth_role='tech'
    with pytest.raises(HTTPException) as err:
        data.adjust_pds_part_stock(part['id'],data.PdsStockAdjustment(delta=1,reason='Unauthorized change'),request)
    assert err.value.status_code==403


def test_pds_stock_ledger_fails_closed_when_corrupt(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'_parts_path',lambda request:tmp_path/'parts_catalog.json')
    request,_=req(tmp_path)
    part=data.create_part(request,data.PartPayload(part_number='TEST'),None)['item']
    (tmp_path/'pds_parts_stock_events.json').write_text('{not valid')
    with pytest.raises(HTTPException) as err:
        data.adjust_pds_part_stock(part['id'],data.PdsStockAdjustment(delta=1,reason='Initial stock'),request)
    assert err.value.status_code==503
    assert (tmp_path/'pds_parts_stock_events.json').read_text()=='{not valid'


def test_customer_eta_email_excludes_internal_references(monkeypatch,tmp_path):
    from app.services import moses_delivery
    request,job=req(tmp_path)
    job.update(customer='Some Customer',customer_email='client@example.com',job_number='SECRET-123',status='Scheduled',scheduled_date='2026-11-20')
    monkeypatch.setattr('app.services.moses_mail_identity.identity', lambda *_:{'from':'office@example.com','reply_to':'office@example.com','cc':[],'issues':[]})
    outcome=moses_delivery.preview_dispatch_eta(request,'pds','j-1','en_route','14:45')
    assert 'SECRET-123' not in outcome['text']
    assert 'SECRET-123' not in outcome['subject']
    assert '760-233-5037' in outcome['text']
    assert 'Our technician is on the way' in outcome['text']
    assert 'job number' not in outcome['text'].lower()
    assert outcome['sent'] is False


def test_week_board_enforces_pds_office_and_lists_only_current_week(tmp_path):
    request,job=req(tmp_path)
    job.update(customer='Acme',job_number='1126-01',date='2026-11-17',scheduled_time='09:00',assigned_employee_ids=['a1'])
    request.app.state.calendar_store.list_jobs=lambda:[dict(job),{'id':'j-2','customer':'Other','date':'2026-11-30'}, {'id':'legacy','date':'2026-11-18','source':'LEGACY_IMPORT'}]
    result=scheduling.office_week(request,'2026-11-16')
    assert result['ok'] and result['count']==1
    assert result['jobs'][0]['customer']=='Acme'
    assert result['jobs'][0]['assigned_names']==['Alice']
    assert 'notes' not in result['jobs'][0]
    with pytest.raises(HTTPException) as err:
        scheduling.office_week(request,'2026-11-17')
    assert err.value.status_code==422
    request.state.auth_role='tech'
    with pytest.raises(HTTPException) as err:
        scheduling.office_week(request,'2026-11-16')
    assert err.value.status_code==403

def test_orb_and_week_scheduler_are_guarded_frontend_features():
    from pathlib import Path
    text=Path(__file__).resolve().parents[1].joinpath('static/app.js').read_text()
    assert 'moses-orb' in text and 'prefers-reduced-motion' in text
    assert "function renderPdsWeekScheduler()" in text
    assert "openDrawer('Job Details',body=>" in text
    assert "renderJobDetails(local,full,{afterSave:refresh,afterDelete:refresh})" in text
    assert "'Update to Schedule'" in text
    assert "if(!confirm('Schedule '+" in text
    assert "ids.length+' technician(s)?'" in text
