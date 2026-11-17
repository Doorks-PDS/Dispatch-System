"""Run against the staged cumulative app router, never production data."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.routers.moses_drafts import SpecificDraftRequest, prepare_specific_job


def job(**updates):
    result = {'id': 'job-42', 'job_number': '1026-73', 'customer': 'Example Customer',
              'status': 'Quote', 'address': 'Verified address', 'completion_forms': [
                  {'id': 'form-1', 'ready_to_quote': True,
                   'recommendations': 'Replace door closer', 'parts_required': 'Closer',
                   'time_required': '2 hours'}]}
    result.update(updates)
    return result


def request(tmp_path, *, platform='pds', role='office_admin', auth=True, record=None):
    saved = record if record is not None else job()
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'office'} if auth else None,
                              auth_role=role), session={'active_platform': platform},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,
            calendar_store=SimpleNamespace(get_job=lambda ident: saved if ident == 'job-42' else None))))


def test_create_exact_job_and_reuse_without_duplicate(tmp_path):
    req=request(tmp_path)
    one=prepare_specific_job(SpecificDraftRequest(record_id='job-42'),req)
    two=prepare_specific_job(SpecificDraftRequest(record_id='job-42'),req)
    assert one['created'] is True and two['existing'] is True
    assert one['item']['id'] == two['item']['id']
    assert one['item']['parts_review'] == 'needs_review'
    assert one['item']['state'] == 'pending_review'
    assert one['no_documents_issued'] and one['approval_required']
    path=Path(tmp_path)/'moses_pds'/'quote_review_drafts.json'
    stored=json.loads(path.read_text())
    assert len(stored)==1
    assert stored[0]['source_form_digest'] and stored[0]['source_form_id']=='form-1'
    assert 'email' not in one['item']


def test_never_rewrites_existing_approved_ticket(tmp_path):
    req=request(tmp_path)
    one=prepare_specific_job(SpecificDraftRequest(record_id='job-42'),req)
    path=Path(tmp_path)/'moses_pds'/'quote_review_drafts.json'
    rows=json.loads(path.read_text());rows[0]['state']='ready_for_estimator';rows[0]['version']=4
    path.write_text(json.dumps(rows));before=path.read_bytes()
    again=prepare_specific_job(SpecificDraftRequest(record_id='job-42'),req)
    assert again['item']['state']=='ready_for_estimator'
    assert again['item']['version']==4
    assert path.read_bytes()==before


@pytest.mark.parametrize('platform,role,auth,code',[
    ('sdc','office_admin',True,403),('doorks','office_admin',True,403),
    ('pds','tech',True,403),('pds','office_admin',False,401)])
def test_workspace_and_role_protection(tmp_path,platform,role,auth,code):
    with pytest.raises(HTTPException) as exc:
        prepare_specific_job(SpecificDraftRequest(record_id='job-42'),request(
            tmp_path,platform=platform,role=role,auth=auth))
    assert exc.value.status_code==code
    assert not (Path(tmp_path)/'moses_pds'/'quote_review_drafts.json').exists()


@pytest.mark.parametrize('record,code',[
    (job(status='Complete'),409),(job(sent_quote_number='RE00075'),409),
    (job(completion_forms=[]),409),(job(completion_forms=[{'ready_to_quote':False}]),409),
    (job(id='some-other-job'),404)])
def test_invalid_job_never_creates_review(tmp_path,record,code):
    with pytest.raises(HTTPException) as exc:
        prepare_specific_job(SpecificDraftRequest(record_id='job-42'),request(tmp_path,record=record))
    assert exc.value.status_code==code
    assert not (Path(tmp_path)/'moses_pds'/'quote_review_drafts.json').exists()


def test_nonexistent_identifier_does_not_write(tmp_path):
    req=request(tmp_path)
    with pytest.raises(HTTPException) as exc:
        prepare_specific_job(SpecificDraftRequest(record_id='unknown'),req)
    assert exc.value.status_code==404


def test_corrupt_existing_ledger_never_replaced(tmp_path):
    path=Path(tmp_path)/'moses_pds'/'quote_review_drafts.json'
    path.parent.mkdir(parents=True)
    path.write_text('BROKEN')
    with pytest.raises(HTTPException) as exc:
        prepare_specific_job(SpecificDraftRequest(record_id='job-42'),request(tmp_path))
    assert exc.value.status_code==503 and path.read_text()=='BROKEN'


def test_http_create_and_retry(tmp_path):
    req=request(tmp_path)
    app=FastAPI()
    @app.middleware('http')
    async def scope_auth(request,next_):
        request.scope['session'] = req.session
        request.state.auth_user = req.state.auth_user
        request.state.auth_role = req.state.auth_role
        request.app.state.data_dir = tmp_path
        request.app.state.calendar_store = req.app.state.calendar_store
        return await next_(request)
    from app.routers.moses_drafts import router
    app.include_router(router)
    client=TestClient(app)
    a=client.post('/moses-drafts/prepare-job',json={'record_id':'job-42'})
    b=client.post('/moses-drafts/prepare-job',json={'record_id':'job-42'})
    assert a.status_code==200 and b.status_code==200
    assert a.json()['created'] and b.json()['existing']
    assert client.get('/moses-drafts').json()['count']==1
