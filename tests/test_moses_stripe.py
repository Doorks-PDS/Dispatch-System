"""Rev80: only test Stripe sessions, simulated provider calls and signed events."""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.services import moses_stripe as stripe
from tests.test_moses_invoice_recipient import req, seed


def configured(monkeypatch):
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED', 'true')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret')
    monkeypatch.setenv('MOSES_PUBLIC_BASE_URL', 'https://portal.example.com')


def setup(tmp_path, monkeypatch, platform='doorks'):
    configured(monkeypatch)
    seed(tmp_path, platform, 'customers', [{'id':'c1', 'name':'Example', 'invoice_email':'ap@example.com'}])
    seed(tmp_path, platform, 'estimates_invoices', [
        {'id':'inv1','customer_id':'c1','document_type':'invoice',
         'document_number':'JS00021', 'status':'Sent', 'total':'125.50',
         'contact_email':'contact@example.com'}])
    return req(tmp_path, platform)


def mock_session(monkeypatch):
    def make(key, row, origin):
        return {'id':'cs_test_session1', 'url':'https://checkout.stripe.com/c/pay/cs_test_session1',
                'mode':'payment','currency':'usd', 'amount_total':row['snapshot']['amount_cents']}
    monkeypatch.setattr(stripe, '_stripe_create', make)


def signed(payload):
    body=json.dumps(payload).encode()
    stamp=int(time.time())
    digest=hmac.new(b'whsec_test_secret', str(stamp).encode()+b'.'+body, hashlib.sha256).hexdigest()
    return body, f't={stamp},v1={digest}'


def event(checkout_id, amount=12550, sid='cs_test_session1'):
    return {'id':'evt_test_1','livemode':False,'type':'checkout.session.completed',
            'data':{'object':{'id':sid, 'client_reference_id':checkout_id,
                              'payment_status':'paid','mode':'payment','currency':'usd',
                              'amount_total':amount,'metadata':{'moses_checkout_id':checkout_id},
                              'payment_intent':'pi_test_123'}}}


def test_approval_payment_and_duplicate_webhook(tmp_path, monkeypatch):
    request=setup(tmp_path, monkeypatch)
    mock_session(monkeypatch)
    row=stripe.propose(request, 'doorks', 'inv1')['proposal']
    assert row['amount_cents']==12550 and row['recipient']=='ap@example.com'
    assert stripe.propose(request, 'doorks', 'inv1')['proposal']['id']==row['id']
    response=stripe.decide(request, 'doorks', row['id'], True)
    assert response['state']=='checkout_ready' and response['payment_created'] is False
    body, sig=signed(event(row['id']))
    assert stripe.webhook(request, body, sig)['processed'] is True
    assert stripe.webhook(request, body, sig)['duplicate'] is True
    assert stripe.history(request, 'doorks', 'inv1')[0]['state']=='paid'
    source=json.loads((tmp_path/'business_workspaces'/'doorks'/'estimates_invoices.json').read_text())[0]
    assert source['status']=='Sent'  # no false automatic paid flag
    with pytest.raises(HTTPException): stripe.propose(request,'doorks','inv1')


def test_rejection_and_stale_invoice(tmp_path, monkeypatch):
    request=setup(tmp_path, monkeypatch)
    a=stripe.propose(request,'doorks','inv1')['proposal']
    assert stripe.decide(request,'doorks',a['id'],False)['state']=='rejected'
    b=stripe.propose(request,'doorks','inv1')['proposal']
    path=tmp_path/'business_workspaces'/'doorks'/'estimates_invoices.json'
    rows=json.loads(path.read_text()); rows[0]['total']='225.50'; path.write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as exc:
        stripe.decide(request,'doorks',b['id'],True)
    assert exc.value.status_code==409


def test_signature_and_mismatched_amount(tmp_path, monkeypatch):
    request=setup(tmp_path,monkeypatch)
    mock_session(monkeypatch)
    row=stripe.propose(request,'doorks','inv1')['proposal']
    stripe.decide(request,'doorks',row['id'],True)
    body,sig=signed(event(row['id'], amount=77777))
    with pytest.raises(HTTPException) as exc:
        stripe.webhook(request,body,sig)
    assert exc.value.status_code==409
    with pytest.raises(HTTPException) as exc:
        stripe.webhook(request,body,'t=1,v1=bad')
    assert exc.value.status_code==400
    body,sig=signed(event(row['id']))
    assert stripe.webhook(request,body,sig)['processed']


def test_workspace_and_disabled_and_draft(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch)
    request.session['active_platform']='sdc'
    with pytest.raises(HTTPException) as exc: stripe.propose(request,'doorks','inv1')
    assert exc.value.status_code==403
    request.session['active_platform']='doorks'
    monkeypatch.delenv('MOSES_STRIPE_TEST_ENABLED')
    with pytest.raises(HTTPException) as exc: stripe.propose(request,'doorks','inv1')
    assert exc.value.status_code==503
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED','true')
    path=tmp_path/'business_workspaces'/'doorks'/'estimates_invoices.json'
    rows=json.loads(path.read_text()); rows[0]['status']='Draft'; path.write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as exc: stripe.propose(request,'doorks','inv1')
    assert exc.value.status_code==409


def test_uncertain_provider_and_reconciliation_hold(tmp_path, monkeypatch):
    request=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(stripe,'_stripe_create',lambda *_: (_ for _ in ()).throw(TimeoutError()))
    row=stripe.propose(request,'doorks','inv1')['proposal']
    assert stripe.decide(request,'doorks',row['id'],True)['state']=='uncertain'
    with pytest.raises(HTTPException): stripe.propose(request,'doorks','inv1')
    request2=setup(tmp_path,monkeypatch,platform='sdc')
    mock_session(monkeypatch)
    proposal=stripe.propose(request2,'sdc','inv1')['proposal']
    stripe.decide(request2,'sdc',proposal['id'],True)
    path=tmp_path/'business_workspaces'/'sdc'/'estimates_invoices.json'
    rows=json.loads(path.read_text());rows[0]['total']='500';path.write_text(json.dumps(rows))
    body,sig=signed(event(proposal['id']))
    result=stripe.webhook(request2,body,sig)
    assert result.get('reconciliation_required')
    assert stripe.history(request2,'sdc','inv1')[0]['state']=='reconciliation_required'


def test_live_key_forbidden(tmp_path,monkeypatch):
    request=setup(tmp_path,monkeypatch)
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_something')
    with pytest.raises(HTTPException) as exc: stripe.propose(request,'doorks','inv1')
    assert exc.value.status_code==503


def test_payment_status_separates_stripe_and_accounting(tmp_path, monkeypatch):
    request = setup(tmp_path, monkeypatch)
    mock_session(monkeypatch)
    proposed = stripe.propose(request, 'doorks', 'inv1')['proposal']
    before = stripe.payment_status(request, 'doorks', 'inv1')
    assert not before['stripe_payment_confirmed']
    assert before['invoice_status'] == 'Sent'
    stripe.decide(request, 'doorks', proposed['id'], True)
    body, sig = signed(event(proposed['id']))
    stripe.webhook(request, body, sig)
    result = stripe.payment_status(request, 'doorks', 'inv1')
    assert result['stripe_payment_confirmed'] is True
    assert result['accounting_reconciled'] is False
    assert result['checkouts'][0]['matches_current_invoice'] is True
    source = json.loads((tmp_path / 'business_workspaces' / 'doorks' / 'estimates_invoices.json').read_text())[0]
    assert source['status'] == 'Sent'


def test_payment_status_detects_changed_invoice_and_permissions(tmp_path, monkeypatch):
    request = setup(tmp_path, monkeypatch)
    mock_session(monkeypatch)
    proposed = stripe.propose(request, 'doorks', 'inv1')['proposal']
    stripe.decide(request, 'doorks', proposed['id'], True)
    body, sig = signed(event(proposed['id']))
    stripe.webhook(request, body, sig)
    path = tmp_path / 'business_workspaces' / 'doorks' / 'estimates_invoices.json'
    rows = json.loads(path.read_text())
    rows[0]['total'] = '250.50'
    path.write_text(json.dumps(rows))
    result = stripe.payment_status(request, 'doorks', 'inv1')
    assert result['stripe_payment_confirmed'] is False
    assert result['stripe_payment_requires_review'] is True
    assert result['checkouts'][0]['stripe_payment_confirmed'] is True
    assert result['checkouts'][0]['matches_current_invoice'] is False
    request.session['active_platform'] = 'sdc'
    with pytest.raises(HTTPException) as exc:
        stripe.payment_status(request, 'doorks', 'inv1')
    assert exc.value.status_code == 403
