"""No automatic linking or posting from name matches."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import pds_qbo_match_review as match


def req(role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role, auth_user={'id':'admin'}),
                           session={'active_platform':'pds'})


def setup(monkeypatch):
    monkeypatch.setattr(match.preview, 'preview_invoice', lambda r,n: {'pds_number':n, 'pds_customer':'Acme Doors LLC'})
    monkeypatch.setattr(match.preview, 'preview_supplier_po', lambda r,n: {'pds_number':n, 'pds_supplier':'Parts Supply'})
    monkeypatch.setattr(match.catalog, 'catalog', lambda r,k,**kw: {
        'company_id':'42','environment':'sandbox','count':2,'next_start':None,
        'records':[{'Id':'10','DisplayName':'ACME  DOORS LLC','Active':True},
                   {'Id':'11','DisplayName':'Acme Doors, LLC','Active':True}]})


def test_exact_only_and_never_approved(monkeypatch):
    setup(monkeypatch)
    result=match.review(req(),'invoice','JS00021')
    assert result['exact_name_candidates']==[{'id':'10','name':'ACME  DOORS LLC','active':True}]
    assert result['review_status']=='manual_review_required'
    assert not result['mapping_saved'] and not result['can_post']
    assert not result['automatic_sync_enabled']


def test_rejects_unauthorized_invalid_and_stale(monkeypatch):
    setup(monkeypatch)
    for role in ('tech','lead','office'):
        with pytest.raises(HTTPException) as e: match.review(req(role),'invoice','JS00021')
        assert e.value.status_code==403
    for kind,start in [('bad',1),('invoice',0)]:
        with pytest.raises(HTTPException) as e: match.review(req(),kind,'JS00021',start=start)
        assert e.value.status_code==422
    def stale(r,n): raise HTTPException(409,'stale')
    monkeypatch.setattr(match.preview,'preview_invoice',stale)
    with pytest.raises(HTTPException) as e: match.review(req(),'invoice','JS00021')
    assert e.value.status_code==409


def test_pagination_is_marked_incomplete(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setattr(match.catalog,'catalog',lambda r,k,**kw:{'company_id':'42','environment':'sandbox',
                         'count':100,'next_start':101,'records':[]})
    result=match.review(req(),'supplier_po','PO-00021')
    assert result['search_incomplete'] and result['next_start']==101
    assert result['exact_name_candidates']==[]
