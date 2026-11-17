import json
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException
import pytest
from app.services.moses_pds_job_context import inspect


class R:
    def __init__(self, path, platform='pds', role='office_admin', auth=True, job=None, docs=None):
        self.state = SimpleNamespace(auth_user={'id': 'admin'} if auth else None, auth_role=role)
        self.session = {'active_platform': platform}
        self.job = job or {'id':'j123','job_number':'1026-73','customer':'The Irvine Company',
                           'status':'Quote','estimate_number':'20106','email':'private@example.com',
                           'completion_forms':[{'ready_to_quote':True,'parts_required':'Latch kits', 'time_required':'8 hours'}]}
        calendar = SimpleNamespace(get_job=lambda id: self.job if id=='j123' else None)
        documents = SimpleNamespace(list_documents=lambda job_id='': docs if docs is not None else [
            {'type':'estimate','number':'20106','job_id':'j123','created_at':'2026-10-30', 'secret':'do not expose'},
            {'type':'invoice','number':'JS00001','job_id':'other','secret':'wrong job'}])
        self.app = SimpleNamespace(state=SimpleNamespace(data_dir=path,calendar_store=calendar,documents_store=documents))


def _saved(root):
    path=Path(root)/'moses_pds'/'quote_review_drafts.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps([{'id':'d1','job_id':'j123','state':'pending_review','customer_email':'secret@example.com'},
                                {'id':'d2','job_id':'unrelated','state':'pending_review'}]))
    return path


def test_joins_exact_job_draft_and_document(tmp_path):
    p=_saved(tmp_path);before=p.read_bytes()
    response=inspect(R(tmp_path),'j123')
    assert response['job']['job_number']=='1026-73'
    assert response['documents']['count']==1
    assert response['documents']['items'][0]['number']=='20106'
    assert response['moses_drafts']['count']==1
    assert response['moses_drafts']['items'][0]['id']=='d1'
    assert 'Review saved Moses quote draft' in response['next_steps'][0]
    assert response['recommendation']['has_parts_requirements']
    assert p.read_bytes()==before
    assert 'private@example.com' not in json.dumps(response)
    assert 'secret@example.com' not in json.dumps(response)
    assert 'do not expose' not in json.dumps(response)


def test_missing_estimate_link_flagged(tmp_path):
    job={'id':'j123','job_number':'1026-73','status':'Quote','estimate_number':'20106', 'completion_forms':[]}
    result=inspect(R(tmp_path,job=job,docs=[]),'j123')
    assert any('no exact linked estimate' in s for s in result['next_steps'])


def test_different_customer_docs_not_inferred(tmp_path):
    result=inspect(R(tmp_path,docs=[{'type':'estimate','number':'20106','job_id':'other'}]),'j123')
    assert result['documents']['count']==0


@pytest.mark.parametrize('platform,role,auth,code',[
    ('sdc','office_admin',True,403),('doorks','office_admin',True,403),
    ('pds','tech',True,403),('pds','office_admin',False,401),
])
def test_scope(tmp_path,platform,role,auth,code):
    with pytest.raises(HTTPException) as exc:
        inspect(R(tmp_path,platform=platform,role=role,auth=auth),'j123')
    assert exc.value.status_code==code


def test_rejects_bad_ids_and_unknown(tmp_path):
    for id in ('../x','', 'a'*81):
        with pytest.raises(HTTPException) as exc: inspect(R(tmp_path),id)
        assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc: inspect(R(tmp_path),'missing')
    assert exc.value.status_code==404


def test_missing_document_store_is_unknown_not_zero(tmp_path):
    req=R(tmp_path)
    req.app.state.documents_store=None
    result=inspect(req,'j123')
    assert result['documents']['available'] is False and result['documents']['count'] is None


def test_broken_drafts_fail_closed(tmp_path):
    path=Path(tmp_path)/'moses_pds'/'quote_review_drafts.json'
    path.parent.mkdir(parents=True);path.write_text('{BROKEN')
    with pytest.raises(HTTPException) as exc: inspect(R(tmp_path),'j123')
    assert exc.value.status_code==503


def test_approved_draft_estimator_next_step(tmp_path):
    p=_saved(tmp_path)
    doc=json.loads(p.read_text());doc[0]['state']='ready_for_estimator';p.write_text(json.dumps(doc))
    result=inspect(R(tmp_path),'j123')
    assert any('existing PDS estimator' in s for s in result['next_steps'])


def test_workflow_status_parts_and_invoice(tmp_path):
    job={'id':'j123','job_number':'1026-73','status':'Parts on Order','completion_forms':[]}
    assert any('receiving' in s for s in inspect(R(tmp_path,job=job),'j123')['next_steps'])
    job['status']='To Be Invoiced'
    assert any('invoice' in s for s in inspect(R(tmp_path,job=job),'j123')['next_steps'])


def test_http_route_verified_workspace(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.moses_action_center import router
    req = R(tmp_path)
    app = FastAPI()
    @app.middleware('http')
    async def attach_scope(request, next_):
        request.scope['session'] = req.session
        request.state.auth_user = req.state.auth_user
        request.state.auth_role = req.state.auth_role
        request.app.state.data_dir = tmp_path
        request.app.state.calendar_store = req.app.state.calendar_store
        request.app.state.documents_store = req.app.state.documents_store
        return await next_(request)
    app.include_router(router)
    client=TestClient(app)
    response=client.get('/moses-action-center/pds/jobs/j123/context')
    assert response.status_code == 200 and response.json()['job']['id']=='j123'
    assert client.get('/moses-action-center/pds/jobs/notthere/context').status_code==404
