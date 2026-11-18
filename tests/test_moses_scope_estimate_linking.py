"""Separate quote scopes must not share/misidentify saved PDS estimate PDFs."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import moses_drafts as m


def _environment(tmp_path, role='office_admin'):
    job={'id':'job-1','job_number':'1126-10','customer':'Example','status':'Quote',
         'completion_forms':[{'id':'form-1','ready_to_quote':True,'recommendations':'Repair separate openings'}]}
    class Jobs:
        def get_job(self, key):return job if key==job['id'] else None
        def list_jobs(self):return [job]
    class Docs:
        def __init__(self):self.rows=[]
        def list_documents(self):return self.rows
    docs=Docs()
    req=SimpleNamespace(state=SimpleNamespace(auth_user={'id':'admin'}, auth_role=role),
       session={'active_platform':'pds'}, app=SimpleNamespace(state=SimpleNamespace(
           data_dir=tmp_path,calendar_store=Jobs(), documents_store=docs)))
    payload=m.SeparateScopesRequest(record_id='job-1',scopes=[
       {'source_form_index':0,'title':'Front entrance','scope':'Repair the front entrance door'},
       {'source_form_index':0,'title':'Side entrance','scope':'Repair the side entrance door'}])
    drafts=m.prepare_job_scopes(payload,req)['items']
    for d in drafts:
        item=d['item'];p=m.DraftEdit(version=item['version'],scope=item['scope'],
               parts_review='none_specified',freight_review='not_required')
        updated=m.update_draft(item['id'],p,req)['item']
        m.decide_draft(item['id'],m.DraftDecision(version=updated['version'],approve=True),req)
    docs.rows=[{'type':'estimate','number':'RE00081','job_id':'job-1','job_number':'1126-10','customer':'Example'},
               {'type':'estimate','number':'RE00082','job_id':'job-1','job_number':'1126-10','customer':'Example'},
               {'type':'estimate','number':'RE00083','job_id':'other','job_number':'1126-10','customer':'Example'}]
    ids=[d['item']['id'] for d in drafts]
    return req,job,docs,ids


def _link(req,draft_id,number):
    current=next(item for item in m.list_drafts(req)['items'] if item['id']==draft_id)
    return m.link_saved_estimate(draft_id,m.LinkSavedEstimate(version=current['version'], estimate_number=number),req)


def test_two_scopes_link_to_two_distinct_existing_estimates(tmp_path):
    req,job,docs,(one,two)=_environment(tmp_path)
    assert m.delivery_documents(one,req)['requires_scope_link'] is True
    assert m.delivery_documents(one,req)['linked_estimate_number'] is None
    first=_link(req,one,'RE00081')
    assert first['ok'] and not first['sent'] and not first['document_created']
    assert m.delivery_documents(one,req)['linked_estimate_number']=='RE00081'
    second=_link(req,two,'RE00082')
    assert second['item']['linked_estimate_number']=='RE00082'
    assert len(docs.rows)==3 and job['status']=='Quote'
    assert m.delivery_documents(two,req)['items'][0]['linked_to_this_scope'] is True


def test_prevent_same_estimate_for_two_scopes_or_switching(tmp_path):
    req,_,_,(one,two)=_environment(tmp_path)
    _link(req,one,'RE00081')
    with pytest.raises(HTTPException) as err:_link(req,two,'RE00081')
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00082')
    assert err.value.status_code==409
    # A repeated request at the current version is idempotent.
    assert _link(req,one,'RE00081')['existing'] is True


def test_job_identity_form_digest_and_document_must_match(tmp_path):
    req,job,docs,(one,two)=_environment(tmp_path)
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00083')
    assert err.value.status_code==409
    job['completion_forms'][0]['recommendations']='Changed by tech'
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00081')
    assert err.value.status_code==409
    job['completion_forms'][0]['recommendations']='Repair separate openings'
    job['customer']='Someone Else'
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00081')
    assert err.value.status_code==409


def test_admin_only_and_stale_version(tmp_path):
    req,_,_,(one,two)=_environment(tmp_path)
    req.state.auth_role='office'
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00081')
    assert err.value.status_code==403
    req.state.auth_role='office_admin'
    with pytest.raises(HTTPException) as err:m.link_saved_estimate(one,m.LinkSavedEstimate(version=1,estimate_number='RE00081'),req)
    assert err.value.status_code==409


def test_link_is_allowed_after_first_sent_quote_but_not_mismatched_source(tmp_path):
    req,job,_,(one,two)=_environment(tmp_path)
    job['sent_quote_number']='RE00081'
    job['status']='Quote Sent'
    assert _link(req,two,'RE00082')['ok']
    assert job['sent_quote_number']=='RE00081'
    assert job['status']=='Quote Sent'


def test_delivery_still_forbids_unapproved_reopened_scope(tmp_path):
    req,_,_,(one,two)=_environment(tmp_path)
    current=next(item for item in m.list_drafts(req)['items'] if item['id']==one)
    m.reopen_draft(one,m.DraftReopen(version=current['version']),req)
    with pytest.raises(HTTPException) as err:m.delivery_documents(one,req)
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:_link(req,one,'RE00081')
    assert err.value.status_code==409


def test_changed_form_after_link_blocks_delivery(tmp_path):
    req,job,_,(one,two)=_environment(tmp_path)
    _link(req,one,'RE00081')
    job['completion_forms'][0]['recommendations']='Modified after linkage'
    with pytest.raises(HTTPException) as err:m.delivery_documents(one,req)
    assert err.value.status_code==409
