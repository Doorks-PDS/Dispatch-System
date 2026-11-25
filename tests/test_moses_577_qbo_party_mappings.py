"""5.77 offline tests: provider party approvals are admin-only and cannot post."""
from types import SimpleNamespace
import hashlib
import json
import pytest
from fastapi import HTTPException
from app.services import pds_qbo_party_mappings as m

FP = 'a'*64

class DummyResponse:
    def __init__(self, data): self.data = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.data[:n]

def request(tmp_path, role='office_admin'):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
                           session={'active_platform':'pds'}, state=SimpleNamespace(auth_role=role,auth_user={'id':'42'}))

def configured(monkeypatch):
    monkeypatch.setattr(m.previews,'preview_invoice',lambda req,num:{'pds_number':num,'pds_customer':'Acme LLC','source_fingerprint':FP})
    monkeypatch.setattr(m.qb,'_mode',lambda req:'online')
    monkeypatch.setattr(m.connection,'configuration',lambda req:{'authorized':True,'last_read_only_verification':'2026-11-24','environment':'sandbox','company_id':'123'})
    monkeypatch.setattr(m.connection,'_environment',lambda:'sandbox')
    monkeypatch.setattr(m.connection,'_access_token',lambda req:('fake','123'))
    monkeypatch.setattr('urllib.request.urlopen',lambda req,timeout: DummyResponse({'QueryResponse':{'Customer':[{'Id':'5','Active':True,'DisplayName':'Acme LLC'}]}}))

def test_explicit_approval_is_local_and_idempotent(tmp_path, monkeypatch):
    configured(monkeypatch); req=request(tmp_path)
    assert m.status(req,'invoice','JS00021')['status']=='not_approved'
    a=m.approve(req,'invoice','JS00021','5',confirm=True)
    assert a['status']=='approved_for_identity_review' and a['can_post'] is False
    assert m.status(req,'invoice','JS00021')['mapping']['provider_id']=='5'
    assert m.approve(req,'invoice','JS00021','5',confirm=True)['status']=='already_approved'
    assert len(json.loads((tmp_path/'pds_qbo_party_approvals.json').read_text())['items'])==1

def test_role_confirmation_and_provider_mismatch(tmp_path,monkeypatch):
    configured(monkeypatch)
    for role in ('lead','tech','office'):
        with pytest.raises(HTTPException) as e: m.approve(request(tmp_path,role),'invoice','JS00021','5',confirm=True)
        assert e.value.status_code==403
    with pytest.raises(HTTPException) as e: m.approve(request(tmp_path),'invoice','JS00021','5')
    assert e.value.status_code==422
    monkeypatch.setattr('urllib.request.urlopen',lambda req,timeout: DummyResponse({'QueryResponse':{'Customer':[{'Id':'5','Active':True,'DisplayName':'Another LLC'}]}}))
    with pytest.raises(HTTPException) as e: m.approve(request(tmp_path),'invoice','JS00021','5',confirm=True)
    assert e.value.status_code==409
    assert not (tmp_path/'pds_qbo_party_approvals.json').exists()

def test_source_edit_or_company_change_invalidates_receipt(tmp_path,monkeypatch):
    configured(monkeypatch);req=request(tmp_path)
    m.approve(req,'invoice','JS00021','5',confirm=True)
    monkeypatch.setattr(m.previews,'preview_invoice',lambda req,num:{'pds_number':num,'pds_customer':'Acme LLC','source_fingerprint':'b'*64})
    assert m.status(req,'invoice','JS00021')['status']=='stale_requires_new_approval'
    with pytest.raises(HTTPException) as e: m.approve(req,'invoice','JS00021','5',confirm=True)
    assert e.value.status_code==409
    monkeypatch.setattr(m.connection,'configuration',lambda req:{'authorized':True,'last_read_only_verification':'2026-11-24','environment':'sandbox','company_id':'999'})
    assert m.status(req,'invoice','JS00021')['status']=='stale_requires_new_approval'
