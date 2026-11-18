"""Van Stock HTTP acceptance with isolated storage. Never uses production inventory."""
import json
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from app.routers import pds_van_stock as van
from app.routers import data as inventory


class Employees:
    def list(self):
        return [{'id':'tech1','name':'Demo Technician','role':'tech'}]


class Users:
    def list_users(self):
        return []


def test_van_stock_http_transfer_reconcile_and_permissions(tmp_path, monkeypatch):
    # Use genuine production endpoint and ledger calculations; only the catalog
    # location is replaced to ensure no production records are ever accessed.
    catalog = tmp_path/'parts_catalog.json'
    catalog.write_text(json.dumps({'items':[
        {'id':'part1','part_number':'DL-1','description':'Demo lock','min_stock':3},
    ]}), encoding='utf-8')
    monkeypatch.setattr(inventory, '_parts_path', lambda request: catalog)
    app=FastAPI()
    app.state.project_root=str(tmp_path)
    app.state.data_dir=str(tmp_path)
    app.state.employees_store=Employees()
    app.state.users_store=Users()

    @app.middleware('http')
    async def auth(request: Request, call_next):
        request.state.auth_user={'id':'office1','name':'Office Tester'}
        request.state.auth_role=request.headers.get('X-Role','office_admin')
        request.session['active_platform']=request.headers.get('X-Platform','pds')
        return await call_next(request)

    app.add_middleware(SessionMiddleware, secret_key='test-only')
    app.include_router(van.router)
    app.include_router(inventory.router)
    inventory._write_json_file(tmp_path/'pds_parts_stock_events.json', [
        {'id':'initial','part_id':'part1','delta':10,'reason':'initial verified count'}
    ])
    with TestClient(app) as client:
        assert client.post('/pds-van-stock/vans',json={'employee_id':'tech1'}).status_code==200
        assert client.put('/pds-van-stock/template',json={'part_id':'part1','minimum':3,'target':5}).status_code==200
        payload={'employee_id':'tech1','part_id':'part1','quantity':4,'movement':'load',
                 'reason':'restock test vehicle','request_id':'test-load-0001'}
        res=client.post('/pds-van-stock/movements',json=payload)
        assert res.status_code==200,res.text
        assert res.json()['van_quantity']==4
        assert client.post('/pds-van-stock/movements',json=payload).json()['duplicate'] is True
        view=client.get('/pds-van-stock').json()
        assert view['catalog'][0]['warehouse']==6
        assert view['vans'][0]['items'][0]['quantity']==4
        assert view['alerts']['vans']==0
        assert client.post('/pds-van-stock/movements',json=dict(payload,quantity=7,request_id='test-load-0002')).status_code==409
        assert client.post('/pds-van-stock/movements',json=dict(payload,quantity=1,request_id='test-load-0003'),headers={'X-Role':'tech'}).status_code==403
        assert client.get('/pds-van-stock',headers={'X-Platform':'sdc'}).status_code==403
        assert client.post('/pds-van-stock/movements',json=dict(payload,movement='used',quantity=2,request_id='test-used-0001')).status_code==200
        view=client.get('/pds-van-stock').json()
        assert view['catalog'][0]['warehouse']==6
        assert view['vans'][0]['items'][0]['quantity']==2
        assert view['alerts']['vans']==1


def test_damaged_parts_catalog_blocks_van_writes(tmp_path, monkeypatch):
    from types import SimpleNamespace
    catalog = tmp_path/'parts_catalog.json'
    catalog.write_text('{malformed', encoding='utf-8')
    monkeypatch.setattr(inventory, '_parts_path', lambda request: catalog)
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        data_dir=str(tmp_path), project_root=str(tmp_path))))
    from fastapi import HTTPException
    from pytest import raises
    with raises(HTTPException) as exc:
        van._parts(request)
    assert exc.value.status_code == 503
    assert 'requires review' in exc.value.detail
    assert not (tmp_path/'pds_van_stock.json').exists()
