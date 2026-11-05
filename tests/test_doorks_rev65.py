import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from app.routers import doorks_portals as portal


def test_portal_home_and_login_protection():
    with TestClient(app) as client:
        assert client.get('/doorks-portals/home').status_code == 200
        assert 'New Inquiry' in client.get('/doorks-portals/home').text
        assert client.get('/doorks-portals/accounts/documents').status_code == 401
        assert client.post('/doorks-portals/accounts/checkout',json={'document_id':'abc'}).status_code == 401


def test_password_hashing():
    h=portal._password_hash('a-long-test-password')
    assert portal._password_valid('a-long-test-password',h)
    assert not portal._password_valid('wrong',h)
    assert 'a-long-test-password' not in h


def test_stripe_webhook_rejects_unsigned(monkeypatch):
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_test123')
    with TestClient(app) as client:
        r=client.post('/doorks-portals/stripe/webhook',content=b'{}')
        assert r.status_code == 400


def test_payroll_diagnostics_route_exists():
    paths={r.path for r in app.routes}
    assert '/doorks-operations/payroll/diagnostics' in paths
    assert '/doorks-operations/payroll/export' in paths
    assert '/doorks-operations/timecards/export' in paths
    assert '/doorks-portals/admin/inquiry-vendor-link' in paths
    assert '/doorks-assistant/chat' in paths


def test_stripe_paid_webhook_is_idempotent(tmp_path,monkeypatch):
    original=getattr(app.state,'data_dir',None)
    app.state.data_dir=tmp_path
    root=tmp_path/'business_workspaces'/'doorks'
    root.mkdir(parents=True)
    customer_id='customer-one'
    invoice_id='invoice-one'
    (root/'customers.json').write_text(json.dumps({'items':[{'id':customer_id,'name':'Customer One'}]}))
    (root/'estimates_invoices.json').write_text(json.dumps({'items':[{'id':invoice_id,'customer_id':customer_id,
        'document_type':'Invoice','document_number':'INV-00001','status':'Sent','amount':107.75,'paid':0}]}))
    account={'id':'account-one','email':'client@example.com','contact_name':'Client','company':'Customer One',
        'customer_id':customer_id,'status':'active','password_hash':portal._password_hash('test-password-long')}
    (root/'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[],
        'payment_links':[],'notifications':[],'accounts':[account],'checkout_sessions':[],'stripe_events':[]}))
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_placeholder')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_test123')
    monkeypatch.setattr(portal,'_stripe_api',lambda endpoint,fields:{'id':'cs_test_123','url':'https://checkout.stripe.com/c/pay/cs_test_123'})
    try:
        with TestClient(app) as client:
            login=client.post('/doorks-portals/accounts/login',json={'email':'client@example.com','password':'test-password-long'})
            assert login.status_code==200,login.text
            checkout=client.post('/doorks-portals/accounts/checkout',json={'document_id':invoice_id})
            assert checkout.status_code==200,checkout.text
            assert checkout.json()['url'].startswith('https://checkout.stripe.com/')
            event={'id':'evt_test_123','type':'checkout.session.completed',
                   'data':{'object':{'id':'cs_test_123','payment_status':'paid','currency':'usd',
                                      'amount_total':10775,'payment_intent':'pi_test_123'}}}
            raw=json.dumps(event).encode()
            timestamp=int(datetime.now(timezone.utc).timestamp())
            sig=hmac.new(b'whsec_test123',str(timestamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
            header={'stripe-signature':f't={timestamp},v1={sig}'}
            first=client.post('/doorks-portals/stripe/webhook',content=raw,headers=header)
            assert first.status_code==200,first.text
            second=client.post('/doorks-portals/stripe/webhook',content=raw,headers=header)
            assert second.status_code==200,second.text
            invoice=json.loads((root/'estimates_invoices.json').read_text())['items'][0]
            assert invoice['paid']==107.75
            assert invoice['stripe_checkout_session_ids']==['cs_test_123']
            docs=client.get('/doorks-portals/accounts/documents')
            assert docs.status_code==200
            assert docs.json()['documents'][0]['balance_due']==0
            payments=client.get('/doorks-portals/accounts/payments')
            assert payments.json()['payments'][0]['amount']==107.75
    finally:
        app.state.data_dir=original
