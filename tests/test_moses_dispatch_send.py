import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_dispatch_send as send


def setup(tmp_path, monkeypatch, platform='doorks'):
    monkeypatch.setenv('MOSES_DISPATCH_SEND_ENABLED','true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','office@example.com')
    monkeypatch.setenv('MOSES_DISPATCH_REPLY_TO','dispatch@example.com')
    monkeypatch.setenv('DOORKS_SMTP_FROM','office@example.com')
    monkeypatch.setenv('DOORKS_SMTP_HOST','smtp.example.com')
    monkeypatch.setenv('DOORKS_SMTP_USERNAME','test')
    monkeypatch.setenv('DOORKS_SMTP_PASSWORD','test')
    job={'id':'j1','job_number':'1126-01','customer':'Customer','email':'customer@example.com',
         'scheduled_date':'2026-11-13','status':'Scheduled'}
    path=tmp_path/'business_workspaces'/'doorks'/'work_orders.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([job]))
    store=SimpleNamespace(get_job=lambda ident: job if ident=='j1' else None)
    req=SimpleNamespace(state=SimpleNamespace(auth_user='admin',auth_role='office_admin'),
       session={'active_platform':platform},app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,calendar_store=store)))
    return req,job,path


def test_approval_and_no_duplicate_sends(tmp_path,monkeypatch):
    req,job,path=setup(tmp_path,monkeypatch)
    sent=[]
    monkeypatch.setattr(send,'_transmit',lambda msg:sent.append(msg.copy()))
    proposal=send.propose(req,'doorks','j1','scheduled')['proposal']
    assert not sent
    result=send.decide(req,'doorks',proposal['id'],True)
    assert result['sent'] and len(sent)==1
    with pytest.raises(HTTPException) as e:
        send.decide(req,'doorks',proposal['id'],True)
    assert e.value.status_code==409
    with pytest.raises(HTTPException):
        send.propose(req,'doorks','j1','scheduled')
    assert send.history(req,'doorks','j1')[0]['state']=='sent'


def test_reject_and_stale_recipient(tmp_path,monkeypatch):
    req,job,path=setup(tmp_path,monkeypatch)
    proposal=send.propose(req,'doorks','j1','en_route','09:30')['proposal']
    assert send.decide(req,'doorks',proposal['id'],False)['state']=='rejected'
    proposal=send.propose(req,'doorks','j1','scheduled')['proposal']
    job['email']='new@example.com'
    path.write_text(json.dumps([job]))
    with pytest.raises(HTTPException) as e:
        send.decide(req,'doorks',proposal['id'],True)
    assert e.value.status_code==409
    assert send.history(req,'doorks','j1')[-1]['state']=='stale'


def test_smtp_error_quarantined(tmp_path,monkeypatch):
    req,job,path=setup(tmp_path,monkeypatch)
    proposal=send.propose(req,'doorks','j1','scheduled')['proposal']
    def outage(msg): raise TimeoutError('unknown smtp status')
    monkeypatch.setattr(send,'_transmit',outage)
    result=send.decide(req,'doorks',proposal['id'],True)
    assert result['state']=='uncertain'
    with pytest.raises(HTTPException): send.decide(req,'doorks',proposal['id'],True)


def test_disabled_and_cross_workspace(tmp_path,monkeypatch):
    req,job,path=setup(tmp_path,monkeypatch)
    req.session['active_platform']='sdc'
    with pytest.raises(HTTPException) as e:
        send.propose(req,'doorks','j1','scheduled')
    assert e.value.status_code==403
    req.session['active_platform']='doorks'
    monkeypatch.delenv('MOSES_DISPATCH_SEND_ENABLED')
    with pytest.raises(HTTPException) as e:
        send.propose(req,'doorks','j1','scheduled')
    assert e.value.status_code==503


def test_pds_isolation_and_explicit_eta(tmp_path,monkeypatch):
    req,job,path=setup(tmp_path,monkeypatch,'pds')
    with pytest.raises(HTTPException): send.propose(req,'pds','j1','en_route')
    proposal=send.propose(req,'pds','j1','en_route','14:30')['proposal']
    assert '14:30' in proposal['text']
    assert 'customer@example.com' in proposal['to']
    assert (tmp_path/'moses_pds'/'moses_dispatch_email_actions.json').exists()
