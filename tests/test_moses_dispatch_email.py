import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_delivery import preview_dispatch_eta


def request(tmp_path, platform='doorks', role='office_admin', pds_job=None):
    store = SimpleNamespace(get_job=lambda _id: pds_job if pds_job and _id == 'job1' else None)
    return SimpleNamespace(state=SimpleNamespace(auth_user='admin', auth_role=role),
        session={'active_platform': platform},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, calendar_store=store)))


def seed(tmp_path):
    folder = tmp_path/'business_workspaces'/'doorks'; folder.mkdir(parents=True)
    (folder/'work_orders.json').write_text(json.dumps([{'id':'job1','job_number':'1126-01',
        'customer':'Acme', 'email':'client@example.com','scheduled_date':'2026-11-13',
        'scheduled_time':'09:00', 'status':'Scheduled'}]))


def test_scheduled_preview_never_sends(tmp_path, monkeypatch):
    seed(tmp_path)
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','dispatch@example.com')
    monkeypatch.setenv('MOSES_DISPATCH_REPLY_TO','office@example.com')
    data=preview_dispatch_eta(request(tmp_path), 'doorks','job1','scheduled')
    assert data['to']=='client@example.com' and '2026-11-13' in data['text']
    assert data['sent'] is False and data['ready_to_send'] is False


def test_enroute_requires_confirmed_eta(tmp_path):
    seed(tmp_path)
    data=preview_dispatch_eta(request(tmp_path),'doorks','job1','en_route')
    assert any('confirmed ETA' in x for x in data['issues'])
    assert 'estimated arrival time is' not in data['text']
    data=preview_dispatch_eta(request(tmp_path),'doorks','job1','en_route','14:30')
    assert '14:30' in data['text']
    with pytest.raises(HTTPException):
        preview_dispatch_eta(request(tmp_path),'doorks','job1','delay','25:90')


def test_workspace_and_role_isolation(tmp_path):
    seed(tmp_path)
    for req, platform in [(request(tmp_path,'sdc'),'doorks'),
                          (request(tmp_path,role='office'),'doorks')]:
        with pytest.raises(HTTPException) as exc:
            preview_dispatch_eta(req,platform,'job1','scheduled')
        assert exc.value.status_code==403


def test_pds_uses_calendar_store_not_doorks_file(tmp_path):
    seed(tmp_path)
    req=request(tmp_path,'pds',pds_job={'id':'job1','customer':'PDS Client',
        'job_number':'1126-02','date':'2026-11-13','email':'pds@example.com'})
    result=preview_dispatch_eta(req,'pds','job1','scheduled')
    assert result['to']=='pds@example.com'
    assert 'Acme' not in result['text']


def test_general_requires_content_and_never_sends(tmp_path):
    seed(tmp_path)
    req=request(tmp_path)
    assert any('update message' in x for x in preview_dispatch_eta(req,'doorks','job1','general')['issues'])
    result=preview_dispatch_eta(req,'doorks','job1','general',note='Access instructions received.')
    assert 'Access instructions received.' in result['text']
    assert result['sent'] is False
