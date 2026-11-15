import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import workspaces


def request(tmp_path, platform='doorks'):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
                           state=SimpleNamespace(auth_user={'id':'admin1'},auth_role='office_admin'),
                           session={'active_platform':platform})


def draft(req, total=300):
    return workspaces.create('doorks','estimates_invoices', workspaces.Record(data={
        'document_type':'Estimate','status':'Draft','description':'Install verified closer',
        'total':total,'document_number':'','source_moses_proposal_id':'proposal1',
        'source_work_order_id':'work1','pricing_required':True,
        'requires_number_assignment':True}), req)['item']


def test_draft_cannot_be_approved_issued_or_forged(tmp_path):
    req=request(tmp_path)
    item=draft(req)
    with pytest.raises(HTTPException) as ex:
        workspaces.update('doorks','estimates_invoices',item['id'],workspaces.Record(data={'status':'Approved'}),req)
    assert ex.value.status_code==409
    updated=workspaces.update('doorks','estimates_invoices',item['id'], workspaces.Record(data={
        'document_number':'RE99999','requires_number_assignment':False,
        'pricing_required':False,'status':'Draft','total':450}),req)['item']
    assert updated['document_number']==''
    assert updated['requires_number_assignment'] is True
    assert updated['pricing_required'] is True
    assert updated['total']==450
    with pytest.raises(HTTPException):
        workspaces.convert_estimate_to_invoice('doorks',item['id'],req)


def test_finalize_requires_explicit_review_and_valid_total(tmp_path):
    req=request(tmp_path)
    item=draft(req,0)
    with pytest.raises(HTTPException) as ex:
        workspaces.finalize_ai_estimate(item['id'],{'confirm_pricing':False},req)
    assert ex.value.status_code==422
    with pytest.raises(HTTPException) as ex:
        workspaces.finalize_ai_estimate(item['id'],{'confirm_pricing':True},req)
    assert ex.value.status_code==409
    assert not (Path(tmp_path)/'business_workspaces/doorks/estimate_sequence.json').exists()


def test_finalize_numbers_monotonically_and_is_idempotent(tmp_path):
    req=request(tmp_path)
    first=draft(req)
    result=workspaces.finalize_ai_estimate(first['id'],{'confirm_pricing':True},req)
    assert result['item']['document_number']=='RE00076'
    assert result['item']['status']=='Ready'
    assert result['sent'] is False
    assert workspaces.finalize_ai_estimate(first['id'],{'confirm_pricing':True},req)['already_numbered']
    other=workspaces.create('doorks','estimates_invoices',workspaces.Record(data={
        'document_type':'Estimate','status':'Draft','description':'second',
        'total':200,'source_moses_proposal_id':'proposal2','pricing_required':True,
        'requires_number_assignment':True}),req)['item']
    result=workspaces.finalize_ai_estimate(other['id'],{'confirm_pricing':True},req)
    assert result['item']['document_number']=='RE00077'
    assert result['item']['status']=='Ready'
    with pytest.raises(HTTPException):
        workspaces.update('doorks','estimates_invoices',other['id'],workspaces.Record(data={'status':'Approved'}),req)


def test_platform_boundary_and_unrelated_estimates_untouched(tmp_path):
    req=request(tmp_path)
    original=workspaces.create('doorks','estimates_invoices',workspaces.Record(data={
        'document_type':'Estimate','status':'Draft','document_number':'OLD-7'}),req)['item']
    with pytest.raises(HTTPException) as ex:
        workspaces.finalize_ai_estimate(original['id'],{'confirm_pricing':True},req)
    assert ex.value.status_code==404
    regular=workspaces.update('doorks','estimates_invoices',original['id'],workspaces.Record(data={'status':'Approved'}),req)['item']
    assert regular['status']=='Approved'
    with pytest.raises(HTTPException) as ex:
        workspaces.finalize_ai_estimate(original['id'],{'confirm_pricing':True},request(tmp_path,'sdc'))
    assert ex.value.status_code==403
