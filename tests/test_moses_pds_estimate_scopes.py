"""Multi-estimate scoping must be read-only, grounded and PDS office restricted."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_pds_estimate_scopes import inspect


def req(*, role='office_admin', platform='pds', auth=True, forms=None):
    job = {'id':'j7','job_number':'1126-07','completion_forms': forms if forms is not None else [
        {'id':'f1','ready_to_quote':True,'door_location':'Hertz','recommendations':'Replace gearbox'},
        {'id':'f2','ready_to_quote':True,'door_location':'All entries','recommendations':'Replace worn weatherstripping on 24 panels'}]}
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'u'} if auth else None,auth_role=role),
        session={'active_platform':platform},app=SimpleNamespace(state=SimpleNamespace(
            calendar_store=SimpleNamespace(get_job=lambda ident: job if ident=='j7' else None))))


def test_multiple_forms_keep_separate_source_provenance():
    result=inspect(req(),'j7')
    assert result['proposed_scope_count']==2
    assert [s['source_form_id'] for s in result['proposed_scopes']]==['f1','f2']
    assert [s['door_location'] for s in result['proposed_scopes']]==['Hertz','All entries']
    assert result['read_only'] and not result['manual_split_required']
    assert 'estimate_number' not in json.dumps(result)


def test_one_form_requesting_multiple_quotes_flagged_not_split_automatically():
    result=inspect(req(forms=[{'id':'a','ready_to_quote':True,'recommendations':
        'Two separate estimates: Hertz operator and all door weatherstripping'}]),'j7')
    assert result['proposed_scope_count']==1
    assert result['manual_split_required']
    assert result['proposed_scopes'][0]['status']=='needs_manual_split'


def test_unmarked_form_not_authorized_as_ready():
    result=inspect(req(forms=[{'recommendations':'Closer replacement'}]),'j7')
    assert result['proposed_scopes'][0]['status']=='needs_quote_readiness_review'
    assert result['proposed_scopes'][0]['source_form_id'] is None


@pytest.mark.parametrize('role,platform,auth,status',[
    ('tech','pds',True,403),('office_admin','sdc',True,403),('office_admin','pds',False,401)])
def test_authorization(role,platform,auth,status):
    with pytest.raises(HTTPException) as exc:
        inspect(req(role=role,platform=platform,auth=auth),'j7')
    assert exc.value.status_code==status


def test_exact_job_required():
    with pytest.raises(HTTPException) as exc:
        inspect(req(),'other')
    assert exc.value.status_code==404
