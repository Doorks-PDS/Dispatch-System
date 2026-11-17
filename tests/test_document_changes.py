import os,sys,importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

SRC=Path(__file__).resolve().parents[1]/'app/services/moses_document_changes.py'
spec=importlib.util.spec_from_file_location('moses_document_changes',SRC)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Store:
    def __init__(self):
        from threading import RLock
        self._lock=RLock()
        self.jobs=[dict(id='a1',job_number='1026-73',estimate_number='',sent_quote_number='',customer='The Irvine Company',address='9530 Towne Center Dr, San Diego, CA 92121',job_notes='Existing tech notes',office_notes='',updated_at='1'),dict(id='a2',job_number='1026-74',estimate_number='999',customer='Test',address='Other',updated_at='1')]
    def list_jobs(self):return self.jobs
    def get_job(self,jid):return next((j for j in self.jobs if j['id']==jid),None)
    def update_job(self,jid,payload):
        x=self.get_job(jid);x.update(payload);x['updated_at']='2';return x

def request(role='office_admin',workspace='pds'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role,auth_user={'id':'admin'}),session={'active_platform':workspace},app=SimpleNamespace(state=SimpleNamespace(calendar_store=Store())))

def test_compare_uses_exact_saved_job_and_preserves_identity():
    r=request();data=mod.compare(r,'1026-73',{'estimate_number':'20106','job_notes':'Proposal from PDF','customer':'BAD','address':'BAD','status':'Complete'})
    assert {c['field'] for c in data['changes']}=={'estimate_number','job_notes'}
    assert data['identity_locked'] and data['read_only'] and not data['records_changed']
    assert r.app.state.calendar_store.get_job('a1')['customer']=='The Irvine Company'

def test_selected_field_only_changes():
    r=request();preview=mod.compare(r,'1026-73',{'estimate_number':'20106','job_notes':'NEW'})
    result=mod.apply(r,'1026-73',preview['version'],{'estimate_number':'20106'},True)
    saved=r.app.state.calendar_store.get_job('a1')
    assert result['updated'] and saved['estimate_number']=='20106' and saved['job_notes']=='Existing tech notes'

def test_rejects_unapproved_and_unselected_changes():
    r=request();snap=mod.compare(r,'1026-73',{'estimate_number':'20106'})['version']
    for args in [({'estimate_number':'20106'},False),({},True),({'customer':'wrong'},True)]:
        with pytest.raises(HTTPException):mod.apply(r,'1026-73',snap,*args)
    assert r.app.state.calendar_store.get_job('a1')['estimate_number']==''

def test_conflict_when_job_changed_after_preview():
    r=request();v=mod.compare(r,'1026-73',{'estimate_number':'20106'})['version'];r.app.state.calendar_store.get_job('a1')['office_notes']='Edited by office'
    with pytest.raises(HTTPException) as e:mod.apply(r,'1026-73',v,{'estimate_number':'20106'},True)
    assert e.value.status_code==409

def test_estimate_link_collision_other_job():
    r=request();r.app.state.calendar_store.get_job('a2')['estimate_number']='20106'
    with pytest.raises(HTTPException) as e:mod.compare(r,'1026-73',{'estimate_number':'20106'})
    assert e.value.status_code==409

def test_permissions():
    for role,workspace in [('technician','pds'),('office_admin','doorks')]:
        with pytest.raises(HTTPException) as e:mod.compare(request(role,workspace),'1026-73',{'estimate_number':'20106'})
        assert e.value.status_code==403

def test_ambiguous_job_numbers_fail_closed():
    r=request();r.app.state.calendar_store.jobs.append({**r.app.state.calendar_store.jobs[0],'id':'a3'})
    with pytest.raises(HTTPException) as e:mod.compare(r,'1026-73',{'estimate_number':'20106'})
    assert e.value.status_code==409

def test_existing_value_replacement_is_disclosed_and_selected():
    r=request();x=mod.compare(r,'1026-73',{'job_notes':'New PDF notes'})
    assert x['changes'][0]['would_replace_existing'] is True
    assert x['changes'][0]['selected'] is False

def test_no_match_never_creates_job():
    r=request();count=len(r.app.state.calendar_store.jobs)
    with pytest.raises(HTTPException):mod.compare(r,'missing',{'estimate_number':'20106'})
    assert len(r.app.state.calendar_store.jobs)==count
