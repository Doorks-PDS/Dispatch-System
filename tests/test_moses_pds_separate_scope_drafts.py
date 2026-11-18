"""Cumulative 5.22: multiple source-linked, unpriced reviews use existing Moses drafts."""
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.routers.moses_drafts import (
    SeparateScopesRequest, prepare_job_scopes, _validate_source,
    _file, _read, _form_digest,
)


def setup(tmp_path, *, role='office_admin', ready=True):
    job = {'id':'job7','job_number':'1126-07','status':'Quote','customer':'Sample',
           'completion_forms':[
                {'id':'a','ready_to_quote':ready,'door_location':'North',
                 'recommendations':'Replace worn weatherstripping'},
                {'id':'b','ready_to_quote':True,'door_location':'South',
                 'recommendations':'Replace leaking gearbox'}]}
    req = SimpleNamespace(state=SimpleNamespace(auth_user={'id':'staff1'},auth_role=role),
                          session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(
                              data_dir=str(tmp_path),calendar_store=SimpleNamespace(get_job=lambda ident: job if ident=='job7' else None))))
    return req, job


def payload(*scopes):
    return SeparateScopesRequest(record_id='job7',scopes=list(scopes))


def scope(index,title,description):
    return {'source_form_index':index,'title':title,'scope':description}


def test_multiple_scopes_same_form_and_other_form(tmp_path):
    req,job=setup(tmp_path)
    entry=payload(scope(0,'North doors','Replace weatherstripping at north entrance'),
                  scope(0,'Side doors','Replace weatherstripping at side entrance'),
                  scope(1,'South doors','Replace leaking south motor gearbox'))
    result=prepare_job_scopes(entry,req)
    assert result['created']==3 and result['no_documents_issued']
    rows=_read(_file(req))
    assert len(rows)==3
    assert [r['source_form_index'] for r in rows]==[0,0,1]
    assert all(r['state']=='pending_review' for r in rows)
    assert [r['source_form_id'] for r in rows]==['a','a','b']
    assert all(r['source_form_digest']==_form_digest(job['completion_forms'][r['source_form_index']]) for r in rows)
    assert prepare_job_scopes(entry,req)['created']==0
    assert len(_read(_file(req)))==3


def test_stale_completion_form_is_rejected_before_approval(tmp_path):
    req,job=setup(tmp_path)
    prepare_job_scopes(payload(scope(0,'North doors','Replace worn north entrance weatherstripping')),req)
    item=_read(_file(req))[0]
    _validate_source(req.app.state.calendar_store,item)
    job['completion_forms'][0]['recommendations']='Changed by technician'
    with pytest.raises(HTTPException) as exc:
        _validate_source(req.app.state.calendar_store,item)
    assert exc.value.status_code==409


def test_invalid_or_unready_form_cannot_make_any_drafts(tmp_path):
    req,job=setup(tmp_path)
    with pytest.raises(HTTPException) as exc:
        prepare_job_scopes(payload(scope(0,'North doors','Long enough description'),scope(3,'Missing','Long enough description')),req)
    assert exc.value.status_code==422
    assert not _file(req).exists()
    job['completion_forms'][0]['ready_to_quote']=False
    with pytest.raises(HTTPException) as exc:
        prepare_job_scopes(payload(scope(0,'North doors','Long enough description')),req)
    assert exc.value.status_code==409
    assert not _file(req).exists()


def test_auth_and_sent_quote_fail_closed(tmp_path):
    req,job=setup(tmp_path,role='tech')
    with pytest.raises(HTTPException) as exc:
        prepare_job_scopes(payload(scope(0,'North doors','Long enough description')),req)
    assert exc.value.status_code==403
    req.state.auth_role='office_admin'
    job['sent_quote_number']='RE00123'
    job['status']='Quote Sent'
    result = prepare_job_scopes(payload(scope(0,'North doors','Long enough description')),req)
    assert result['created'] == 1 and result['no_documents_issued']
    assert job['status'] == 'Quote Sent' and job['sent_quote_number'] == 'RE00123'


def test_duplicate_submitted_scopes_rejected(tmp_path):
    req,_=setup(tmp_path)
    with pytest.raises(HTTPException) as exc:
        prepare_job_scopes(payload(scope(0,'North doors','Replace worn entrance weatherstripping'),
                                   scope(0,'North doors','Replace worn entrance weatherstripping')),req)
    assert exc.value.status_code==422
    assert not _file(req).exists()


def test_additional_scopes_after_first_estimate_sent_need_independent_approval(tmp_path):
    from app.routers import moses_drafts as m
    req, job = setup(tmp_path)
    job.update(status='Quote Sent', sent_quote_number='RE00091')
    result = prepare_job_scopes(payload(scope(0, 'Additional side door',
        'Replace additional worn weatherstrip at the side entry')), req)
    assert result['created'] == 1
    item = result['items'][0]['item']
    assert item['state'] == 'pending_review'
    m._validate_source(req.app.state.calendar_store, m._read(m._file(req))[0])
    assert job['status'] == 'Quote Sent' and job['sent_quote_number'] == 'RE00091'
    # Legacy single-job preparation remains blocked after the first send.
    with pytest.raises(HTTPException) as error:
        m.prepare_specific_job(m.SpecificDraftRequest(record_id='job7'), req)
    assert error.value.status_code == 409


def test_multi_scope_after_sent_still_rejects_closed_job_or_changed_source(tmp_path):
    req, job = setup(tmp_path)
    job.update(status='Quote Sent', sent_quote_number='RE00091')
    prepare_job_scopes(payload(scope(0, 'Side entry',
        'Additional recommendation at the side entrance')), req)
    record = _read(_file(req))[0]
    job['completion_forms'][0]['recommendations'] = 'Different recommendation'
    with pytest.raises(HTTPException) as error:
        _validate_source(req.app.state.calendar_store, record)
    assert error.value.status_code == 409
    job['completion_forms'][0]['recommendations'] = 'Replace worn weatherstripping'
    job['status'] = 'Done'
    with pytest.raises(HTTPException) as error:
        _validate_source(req.app.state.calendar_store, record)
    assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        prepare_job_scopes(payload(scope(1, 'Other opening',
            'Another recommendation at the other entrance')), req)
    assert error.value.status_code == 409
