"""Release 5.46 field-owned vehicle permissions and human-readable audit.

Entirely in temp storage. No production app/user data is opened or written.
"""
import json
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from app.routers import pds_van_stock as van
from app.routers import data as inventory


class Employees:
    def list(self):
        return [
            {'id':'van1','name':'Test Tech','role':'tech','active':True,'login_user_id':'user1'},
            {'id':'van2','name':'Second Tech','role':'tech','active':True,'login_user_id':'user2'},
            {'id':'old','name':'Former Tech','role':'tech','active':False,'login_user_id':'olduser'},
        ]


class Users:
    def list_users(self):
        return [
            {'id':'user1','name':'Test Tech','role':'tech','active':True},
            {'id':'user2','name':'Second Tech','role':'tech','active':True},
            {'id':'olduser','name':'Former Tech','role':'tech','active':False},
        ]


def test_self_managed_van_usage_audit_and_cross_van_protection(tmp_path,monkeypatch):
    catalog=tmp_path/'parts_catalog.json'
    catalog.write_text(json.dumps({'items':[{'id':'part1','part_number':'311S','description':'Closer','min_stock':1}]}))
    monkeypatch.setattr(inventory,'_parts_path',lambda request:catalog)
    app=FastAPI()
    app.state.project_root=str(tmp_path)
    app.state.data_dir=str(tmp_path)
    app.state.employees_store=Employees()
    app.state.users_store=Users()

    @app.middleware('http')
    async def authenticate(request:Request,call_next):
        role=request.headers.get('X-Role','office_admin')
        if role=='tech':
            request.state.auth_user={'id':'user1','name':'Test Tech','role':'tech'}
        elif role=='lead':
            request.state.auth_user={'id':'user2','name':'Second Tech','role':'lead'}
        else:
            request.state.auth_user={'id':'office1','name':'Office Manager','role':'office_admin'}
        request.state.auth_role=role
        request.session['active_platform']=request.headers.get('X-Platform','pds')
        return await call_next(request)

    app.add_middleware(SessionMiddleware,secret_key='local-test')
    app.include_router(van.router)
    app.include_router(inventory.router)
    inventory._write_json_file(tmp_path/'pds_parts_stock_events.json',[
        {'id':'initial','part_id':'part1','delta':10,'reason':'verified opening warehouse count'}
    ])
    with TestClient(app) as client:
        for person in ('van1','van2'):
            assert client.post('/pds-van-stock/vans',json={'employee_id':person}).status_code==200
        assert client.put('/pds-van-stock/vans/van1/items',headers={'X-Role':'tech'},json={
            'part_id':'part1','minimum':1,'target':3
        }).status_code==200
        assert client.put('/pds-van-stock/vans/van2/items',headers={'X-Role':'tech'},json={
            'part_id':'part1','minimum':1,'target':3
        }).status_code==403
        assert client.put('/pds-van-stock/template',headers={'X-Role':'tech'},json={
            'part_id':'part1','minimum':1,'target':3
        }).status_code==403
        assert client.post('/pds-van-stock/movements',headers={'X-Role':'tech'},json={
            'employee_id':'van1','part_id':'part1','quantity':2,'movement':'load',
            'reason':'Not an authorized transfer','request_id':'tech-load-0001'
        }).status_code==403
        assert client.post('/pds-van-stock/movements',json={
            'employee_id':'van1','part_id':'part1','quantity':5,'movement':'load',
            'reason':'Warehouse issued to tech','request_id':'office-load-0001'
        }).status_code==200
        used={'employee_id':'van1','part_id':'part1','quantity':2,'movement':'used',
              'reason':'Job 1126-15 closer replacement','request_id':'tech-used-0001'}
        assert client.post('/pds-van-stock/movements',headers={'X-Role':'tech'},json=used).status_code==200
        assert client.post('/pds-van-stock/movements',headers={'X-Role':'tech'},json=used).json()['duplicate']
        view=client.get('/pds-van-stock',headers={'X-Role':'tech'}).json()
        assert view['catalog'][0]['warehouse']==5
        own=next(row for row in view['vans'] if row['employee_id']=='van1')
        other=next(row for row in view['vans'] if row['employee_id']=='van2')
        assert own['can_edit'] is True
        assert other['can_edit'] is False
        latest=own['recent_movements'][0]
        assert 'Used 2 × 311S' in latest['summary']
        assert latest['performed_by']=='Test Tech'
        assert latest['quantity_before']==5 and latest['quantity_after']==3
        assert latest['warehouse_effect']==0
        assert client.post('/pds-van-stock/movements',headers={'X-Role':'tech'},json={
            **used,'employee_id':'van2','request_id':'tech-other-0001'
        }).status_code==403
        assert client.post('/pds-van-stock/vans',headers={'X-Role':'tech'},json={
            'employee_id':'van1','enabled':False
        }).status_code==403
        history=client.get('/pds-van-stock/history',headers={'X-Role':'tech'}).json()['items']
        assert history and all(row['employee_id']=='van1' for row in history)
        assert any('Updated part1' in row['description'] for row in history)
        assert client.get('/pds-van-stock/history',headers={'X-Platform':'sdc'}).status_code==403


def test_fleet_ui_has_owner_edit_controls_and_readable_history():
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'static/app.js').read_text()
    for needle in ('Fleet Hub','van.can_edit','Stock History · Who changed what',
                   'event.quantity_before','event.quantity_after',"'✉ Notify Customer'",
                   'Adjust Stock','Last Upload','Customer & Contact Directory'):
        assert needle in js, needle
