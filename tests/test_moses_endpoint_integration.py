from __future__ import annotations
import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_moses_action_center import Request, _draft, connected

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def _app(request):
    from app.routers.moses_action_center import router
    app=FastAPI()
    @app.middleware('http')
    async def attach_scope(req, next_):
        req.scope['session']=request.session
        req.state.auth_user=request.state.auth_user
        req.state.auth_role=request.state.auth_role
        req.app.state.data_dir=request.app.state.data_dir
        req.app.state.calendar_store=request.app.state.calendar_store
        return await next_(req)
    app.include_router(router)
    return app


def test_verified_http_api_returns_saved_workspace_sources(connected):
    _draft(connected)
    request=Request(connected,jobs=[{'id':'j1','job_number':'1026-73','customer':'Irvine','status':'Quote'}])
    c=TestClient(_app(request))
    result=c.get('/moses-action-center/overview')
    assert result.status_code==200,result.text
    data=result.json()
    assert data['drafts']['count']==1 and data['work']['count']==1
    details=c.get('/moses-action-center/pds/drafts/d123')
    assert details.status_code==200 and details.json()['draft']['job_id']=='j1'


def test_http_api_denies_other_business_access(connected):
    _draft(connected)
    c=TestClient(_app(Request(connected,platform='sdc')))
    assert c.get('/moses-action-center/pds/drafts/d123').status_code==403
    assert c.get('/moses-action-center/overview').json()['drafts']['items']==[]


def test_http_api_denies_field_role(connected):
    c=TestClient(_app(Request(connected,role='tech')))
    assert c.get('/moses-action-center/overview').status_code==403
