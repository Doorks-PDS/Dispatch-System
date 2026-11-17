"""Check PDS document approval bridge using the saved PDS sender interface.

No provider network calls, no real customer documents or data files.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException, FastAPI
from fastapi.testclient import TestClient
from app.services import moses_pds_document_actions as actions
from app.services.moses_pds_document_intent import is_pds_document_mail_request


class DummyDelivery:
    sent=0
    def _guard(self, req):
        if not getattr(req.state,'auth_user',None):raise HTTPException(401,'Sign in')
        if req.session.get('active_platform')!='pds' or req.state.auth_role!='office_admin':
            raise HTTPException(403,'PDS only')
    def preview(self, req, kind, number):
        self._guard(req)
        return {'kind':kind,'number':number,'to':'verified@example.com','attachment_verified':True}
    def history(self, req, kind, number):
        self._guard(req)
        return [{'state':'sent','number':number}]
    def propose(self, req, kind, number):
        self._guard(req)
        return {'proposal':{'id':'a'*32,'state':'pending','kind':kind,'number':number,
                 'job_number':'1026-73','to':'verified@example.com','from':'estimates@example.com',
                 'subject':'Estimate '+number,'filename':number+'.pdf','sent':False}}
    def _file(self, req):return Path(req.app.state.data_dir)/'delivery.json'
    class _Lock:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    def _locked(self,path):return self._Lock()
    def _load(self,path):
        return [{'id':'a'*32,'state':'pending','snapshot':{'kind':'estimate','number':'RE00075',
                'job_number':'1026-73','to':'verified@example.com','from':'estimates@example.com',
                'subject':'Estimate RE00075','filename':'RE00075.pdf'}}]
    def _public(self,row):
        return {'id':row['id'],'state':row['state'],**row['snapshot']}


def request(platform='pds',role='office_admin',signed=True):
    return SimpleNamespace(session={'active_platform':platform},
      state=SimpleNamespace(auth_user=({'id':'admin'} if signed else None),auth_role=role,
                            moses_document_proposals=[]),
      app=SimpleNamespace(state=SimpleNamespace(data_dir='/tmp')))

@pytest.fixture
def mock_delivery():
    with patch.object(actions,'_guard',side_effect=lambda req: validated(req)):
        yield


def validated(req):
    delivery=DummyDelivery();delivery._guard(req);return delivery


def test_saved_document_proposal_and_review_are_not_sends(mock_delivery):
    req=request()
    data=actions.review(req,'estimate','re00075')
    assert data['document']['number']=='RE00075' and data['read_only']
    proposal=actions.prepare(req,'estimate','RE00075')
    assert not proposal['sent'] and proposal['approval_required']
    assert req.state.moses_document_proposals[0]['id']=='a'*32
    inbox=actions.pending(req)
    assert inbox['count']==1 and inbox['proposals'][0]['kind']=='pds_document_email'
    assert DummyDelivery.sent==0

@pytest.mark.parametrize('platform,role,signed',[
    ('sdc','office_admin',True),('doorks','office_admin',True),('pds','tech',True),('pds','office_admin',False)])
def test_workspace_and_role_isolation(platform,role,signed,mock_delivery):
    with pytest.raises(HTTPException):actions.prepare(request(platform,role,signed),'estimate','RE00075')

@pytest.mark.parametrize('kind,number',[
    ('invoice','RE00075'),('estimate','JS00020'),('estimate','../../escape'),
    ('estimate',''),('anything','RE00075')])
def test_invalid_numbers_fail_closed(kind,number,mock_delivery):
    with pytest.raises(HTTPException) as e:actions.prepare(request(),kind,number)
    assert e.value.status_code==422

@pytest.mark.parametrize('message,expected',[
    ('Moses send estimate RE00075 to the customer',True),
    ('Email invoice JS00020',True),
    ('Forward that PDF to the customer',True),
    ('Which jobs need to be quoted?',False),
    ('Prepare an estimate for the Irvine job',False),
    ('What are my invoices?',False),
    ('Send technician to site',False)])
def test_natural_language_intent_only_explicit_document_mail(message,expected):
    assert is_pds_document_mail_request(message)==expected


def test_http_pending_queue_uses_existing_backend_and_auth(mock_delivery):
    from app.routers.moses_action_center import router
    app=FastAPI()
    @app.middleware('http')
    async def scopes(r,next_):
        r.scope['session']={'active_platform':'pds'}
        r.state.auth_user={'id':'admin'}
        r.state.auth_role='office_admin'
        r.app.state.data_dir='/tmp'
        return await next_(r)
    app.include_router(router)
    result=TestClient(app).get('/moses-action-center/pds/document-emails/pending')
    assert result.status_code==200 and result.json()['count']==1


def test_no_untrusted_arbitrary_recipient_or_provider_invocation(mock_delivery):
    proposal=actions.prepare(request(),'invoice','JS00020')['proposal']
    assert proposal['to']=='verified@example.com'
    assert 'message' not in proposal and 'html' not in proposal
    assert 'approved' not in proposal
