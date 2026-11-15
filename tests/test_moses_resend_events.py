"""Signed Resend events only observe delivery; never modify business records."""
import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.services import moses_resend_events as events


def make_request(tmp_path, platform='pds', headers=None):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
        state=SimpleNamespace(auth_user={'id':'admin'}, auth_role='office_admin'),
        session={'active_platform':platform}, headers=headers or {})


def signed(monkeypatch, payload, timestamp=None, event_id='msg_001'):
    key=b'test-secret-1234567890'
    monkeypatch.setenv('RESEND_WEBHOOK_SECRET','whsec_'+base64.b64encode(key).decode())
    body=json.dumps(payload).encode()
    stamp=str(int(time.time()) if timestamp is None else timestamp)
    sig=base64.b64encode(hmac.new(key,event_id.encode()+b'.'+stamp.encode()+b'.'+body,hashlib.sha256).digest()).decode()
    return body, {'svix-id':event_id,'svix-timestamp':stamp,'svix-signature':'v1,'+sig}


def payload(kind='email.delivered',id='email_test123'):
    return {'type':kind,'created_at':'2026-11-12T17:00:00Z',
            'data':{'email_id':id,'to':['private@example.com'],'subject':'secret attachment link'}}


def test_verified_event_matches_only_correct_workspace(tmp_path,monkeypatch):
    from app.routers.workspaces import save
    key='email_test123'
    path=tmp_path/'business_workspaces'/'doorks'/'moses_po_delivery_actions.json'
    path.parent.mkdir(parents=True)
    save(path,[{'id':'proposal1','record_id':'poA','state':'sent','provider_message_id':key,'delivery_status':'accepted_by_provider'}])
    body, headers=signed(monkeypatch,payload())
    req=make_request(tmp_path,'doorks',headers)
    assert events.receive(req,body)=={'received':True,'tracked':True,'duplicate':False}
    assert events.receive(req,body)['duplicate'] is True
    result=events.status(req,'doorks','purchase_order','poA')
    assert result['items'][0]['delivery_status']=='delivered_to_recipient_server'
    assert result['items'][0]['delivery_event_at']
    assert events.status(req,'doorks','purchase_order','poB')=={'items':[]}
    assert 'secret' not in (tmp_path/'moses_resend_delivery_events.json').read_text()
    with pytest.raises(HTTPException) as e:
        events.status(req,'sdc','purchase_order','poA')
    assert e.value.status_code==403
    assert __import__('json').loads(path.read_text())[0]['delivery_status'] == 'accepted_by_provider'


def test_signatures_forgery_and_stale_are_rejected(tmp_path,monkeypatch):
    body, headers=signed(monkeypatch,payload())
    req=make_request(tmp_path,headers=headers)
    assert events.verify(body,headers)[1]['type']=='email.delivered'
    with pytest.raises(HTTPException):
        events.receive(req,body+b' ')
    stale_body, stale_headers=signed(monkeypatch,payload(),timestamp=int(time.time())-3600)
    with pytest.raises(HTTPException):
        events.receive(make_request(tmp_path,headers=stale_headers),stale_body)
    with pytest.raises(HTTPException):
        events.verify(body,{'svix-id':'bad','svix-timestamp':headers['svix-timestamp'],'svix-signature':headers['svix-signature']})


def test_bounce_and_out_of_order_events_are_observable(tmp_path,monkeypatch):
    path=tmp_path/'moses_pds'/'moses_dispatch_email_actions.json'
    path.parent.mkdir(parents=True)
    from app.routers.workspaces import save
    save(path,[{'id':'dispatch1','record_id':'job1','state':'sent','provider_message_id':'email_test123'}])
    r=make_request(tmp_path)
    for i,kind in enumerate(('email.bounced','email.sent')):
        item=payload(kind)
        item['created_at']=('2026-11-12T17:10:00Z' if i==0 else '2026-11-12T17:00:00Z')
        body, headers=signed(monkeypatch,item,event_id='msg_'+str(i))
        r.headers=headers
        assert events.receive(r,body)['tracked']
    observed=events.status(r,'pds','dispatch','job1')['items'][0]
    assert observed['delivery_status']=='bounced'
    assert observed['state']=='sent'  # an email send is never undone by delivery observation


def test_unmatched_event_can_be_correlated_after_save(tmp_path,monkeypatch):
    r=make_request(tmp_path,'sdc')
    body,headers=signed(monkeypatch,payload('email.failed','email_delayed'))
    r.headers=headers
    events.receive(r,body)
    assert events.status(r,'sdc','invoice','invoice1')=={'items':[]}
    from app.routers.workspaces import save
    path=tmp_path/'business_workspaces'/'sdc'/'moses_invoice_delivery_actions.json'
    path.parent.mkdir(parents=True)
    save(path,[{'id':'email1','record_id':'invoice1','state':'sent','provider_message_id':'email_delayed'}])
    assert events.status(r,'sdc','invoice','invoice1')['items'][0]['delivery_status']=='failed'


@pytest.mark.parametrize('bad_signature', ['v1,%%%%', 'v1,abc', 'v1,' + 'X' * 5000])
def test_malformed_signature_headers_rejected_without_server_error(monkeypatch, bad_signature):
    body, headers = signed(monkeypatch, payload())
    headers['svix-signature'] = bad_signature
    with pytest.raises(HTTPException) as err:
        events.verify(body, headers)
    assert err.value.status_code == 400


@pytest.mark.parametrize('bad_stamp', ['9' * 6000, '9999999999999', 'invalid'])
def test_malformed_timestamps_rejected_without_server_error(monkeypatch, bad_stamp):
    body, headers = signed(monkeypatch, payload())
    headers['svix-timestamp'] = bad_stamp
    with pytest.raises(HTTPException) as err:
        events.verify(body, headers)
    assert err.value.status_code == 400


def test_delivery_status_is_read_only_without_existing_storage(tmp_path):
    missing_dir = tmp_path / 'not-yet-created'
    request = make_request(missing_dir, 'doorks')
    assert events.status(request, 'doorks', 'invoice', 'unknown') == {'items': []}
    assert not missing_dir.exists(), 'Status lookup must not create persistent-data directories'

def test_delivery_status_does_not_create_lock_when_event_ledger_missing(tmp_path):
    from app.routers.workspaces import save
    path = tmp_path / 'business_workspaces' / 'doorks' / 'moses_invoice_delivery_actions.json'
    path.parent.mkdir(parents=True)
    save(path, [{'id':'proposal1','record_id':'invoice1','state':'sent',
                 'provider_message_id':'email_test123','delivery_status':'accepted_by_provider'}])
    request = make_request(tmp_path, 'doorks')
    assert events.status(request, 'doorks', 'invoice', 'invoice1')['items'][0]['delivery_status'] == 'accepted_by_provider'
    assert not (tmp_path / 'moses_resend_delivery_events.lock').exists()
