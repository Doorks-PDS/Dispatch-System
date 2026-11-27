"""Moses 5.94: complete PDS cart -> details -> review -> secure sandbox checkout."""
from pathlib import Path
import uuid
import json
import asyncio
import pytest
from fastapi import HTTPException

from app.routers import pds_parts_store as store
from tests.test_pds_parts_store_592 import request, seed, settings, fake_stripe, event, signed

ROOT = Path(__file__).resolve().parents[1]


def test_cart_quote_never_exposes_supplier_prices(tmp_path, monkeypatch):
    rows, path = seed(monkeypatch, tmp_path)
    req = request(tmp_path, role=None)
    quote = store.cart_quote(req, store.Cart(lines=[store.Line(id='p1', qty=2)], token=uuid.uuid4()))
    assert quote['subtotal_cents'] == 44000
    assert quote['shipping_cents'] is None
    assert quote['checkout_mode'] == 'off'
    assert 'supplier' not in str(quote)
    rows[0]['price'] = '235.00'
    path.write_text(json.dumps({'items': rows}))
    update = store.cart_quote(req, store.Cart(lines=[store.Line(id='p1', qty=2)], token=uuid.uuid4()))
    assert update['subtotal_cents'] == 47000


def test_cart_quote_in_test_checkout_includes_verified_shipping(tmp_path, monkeypatch):
    seed(monkeypatch, tmp_path)
    settings(monkeypatch)
    req = request(tmp_path, role=None)
    result = store.cart_quote(req, store.Cart(lines=[store.Line(id='p1', qty=1)], token=uuid.uuid4()))
    assert result['checkout_mode'] == 'test'
    assert result['shipping_cents'] == 1200
    assert result['before_tax_cents'] == 23200
    assert 'Stripe' in result['tax_note']
    with pytest.raises(HTTPException) as e:
        store.cart_quote(req, store.Cart(lines=[store.Line(id='p2', qty=1)], token=uuid.uuid4()))
    assert e.value.status_code == 409


def test_sandbox_checkout_contact_prefills_stripe_and_keeps_separate_ledger(tmp_path, monkeypatch):
    rows, path = seed(monkeypatch, tmp_path)
    settings(monkeypatch)
    original = store._stripe_session
    def provider(key, record, origin, shipping):
        form = store._checkout_payload(record, origin, shipping)
        assert form['customer_email'] == 'buyer@example.com'
        assert '{CHECKOUT_SESSION_ID}' in form['success_url']
        assert form['shipping_address_collection[allowed_countries][0]'] == 'US'
        assert form['line_items[0][quantity]'] == '2'
        assert record['customer_name'] == 'Sample Buyer'
        return {'id':'cs_test_abcdefghij1234567890','url':'https://checkout.stripe.com/c/pay/cs_test_sample',
                'mode':'payment','currency':'usd','amount_subtotal':44000}
    monkeypatch.setattr(store, '_stripe_session', provider)
    req = request(tmp_path, role=None)
    payload=store.Cart(lines=[store.Line(id='p1',qty=2)],token=uuid.uuid4(),name='Sample Buyer',
                       email='Buyer@Example.com',phone='555-4321',postal_code='92001')
    result=store.checkout(req,payload)
    assert result['checkout_url'].startswith('https://checkout.stripe.com/')
    saved=store._load(store._orders_path(req))[0]
    assert saved['state']=='checkout_pending'
    assert saved['customer_email']=='buyer@example.com'
    assert saved['customer_phone']=='555-4321'
    assert saved['postal_code']=='92001'
    assert saved.get('paid_at') is None
    assert store.checkout(req,payload)==result  # same request idempotent
    assert json.loads(path.read_text())['items']==rows
    monkeypatch.setattr(store,'_stripe_session',original)


def test_checkout_rejects_bad_email(tmp_path, monkeypatch):
    seed(monkeypatch,tmp_path)
    settings(monkeypatch)
    req=request(tmp_path)
    bad=store.Cart(lines=[store.Line(id='p1',qty=1)],token=uuid.uuid4(),email='bad@@example.com')
    with pytest.raises(HTTPException) as e:
        store.checkout(req,bad)
    assert e.value.status_code==422
    assert not store._orders_path(req).exists()


def test_order_request_shipping_address_and_no_payment(tmp_path, monkeypatch):
    rows,path=seed(monkeypatch,tmp_path)
    req=request(tmp_path,role=None)
    payload=store.OrderRequest(lines=[store.Line(id='p1',qty=1)],token=uuid.uuid4(),
                               name='Demo Buyer',email='buyer@example.com',postal_code='92001',
                               shipping_line1='123 Main Street',shipping_line2='Suite 2',
                               shipping_city='San Diego',shipping_state='CA')
    response=store.request_order(req,payload)
    assert response['payment_received'] is False
    record=store._load(store._orders_path(req))[0]
    assert record['shipping_address']=={'line1':'123 Main Street','line2':'Suite 2',
                                        'city':'San Diego','state':'CA','postal_code':'92001','country':'US'}
    assert record['paid_at'] is None and record['state']=='requested'
    assert json.loads(path.read_text())['items']==rows
    with pytest.raises(HTTPException) as e:
        store.sdc_update_order(record['id'],store.OrderUpdate(status='shipped'),request(tmp_path,role='office_admin',platform='sdc'))
    assert e.value.status_code==409


def test_order_request_rejects_partial_address(tmp_path, monkeypatch):
    seed(monkeypatch,tmp_path)
    req=request(tmp_path,role=None)
    payload=store.OrderRequest(lines=[store.Line(id='p1',qty=1)],token=uuid.uuid4(),
                               name='Demo Buyer',email='buyer@example.com',shipping_line1='123 Main')
    with pytest.raises(HTTPException) as e:store.request_order(req,payload)
    assert e.value.status_code==422


def test_payment_return_cannot_claim_payment_before_signed_webhook(tmp_path, monkeypatch):
    seed(monkeypatch,tmp_path);settings(monkeypatch)
    def provider(key,record,origin,shipping):
        return {'id':'cs_test_abcdefghij1234567890','url':'https://checkout.stripe.com/c/pay/cs_test_abc',
                'mode':'payment','currency':'usd','amount_subtotal':44000}
    monkeypatch.setattr(store,'_stripe_session',provider)
    req=request(tmp_path,role=None)
    payload=store.Cart(lines=[store.Line(id='p1',qty=2)],token=uuid.uuid4())
    store.checkout(req,payload)
    pending=store.checkout_status(req,'cs_test_abcdefghij1234567890')
    assert pending['payment_status']=='pending'
    assert pending['order_status']=='processing'
    assert set(pending)=={'reference','payment_status','order_status','test_mode'}
    with pytest.raises(HTTPException):store.checkout_status(req,'cs_test_not_known_0000000')
    row=store._load(store._orders_path(req))[0]
    paid_event=event(row)
    paid_event['data']['object']['id']='cs_test_abcdefghij1234567890'
    raw,sig=signed(paid_event)
    async def body():return raw
    req.body=body;req.headers={'stripe-signature':sig}
    assert asyncio.run(store.stripe_webhook(req))['processed'] is True
    confirmed=store.checkout_status(req,'cs_test_abcdefghij1234567890')
    assert confirmed['payment_status']=='paid' and confirmed['order_status']=='paid'


def test_checkout_page_has_complete_flow_and_no_live_shortcut():
    html=(ROOT/'static/pds_parts_store.html').read_text(encoding='utf-8')
    for id_name in ('flowCart','flowContact','flowReview','orderSummary','checkoutDialog','paymentBanner'):
        assert 'id="'+id_name+'"' in html
    assert 'cart-quote' in html and 'checkout-status' in html
    assert 'sessionStorage' in html  # ephemeral cart only, no PDS customer ledger in browser
    assert '/pds-parts/api/order-requests' in html
    assert 'checkout.stripe.com' in html
