"""Moses 5.92: PDS store safety, shared catalog, Stripe opt-in and webhook tests."""
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import pds_parts_store as store
from app.routers import data as pds_data


def request(tmp, role='office_admin', platform='pds'):
    root = Path(tmp)
    (root/'static').mkdir(exist_ok=True)
    return SimpleNamespace(
        state=SimpleNamespace(auth_role=role, auth_user={'id': 'admin1'} if role else None),
        session={'active_platform': platform},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(root), project_root=str(root))),
    )


def seed(monkeypatch, tmp):
    parts_path = tmp/'parts_catalog.json'
    rows = [
        {'id':'p1', 'part_number':'VD-987', 'description':'Panic bar exit device', 'manufacturer':'Von Duprin',
         'price':'220.00','supplier_rate':'135.00','supplier':'Company Private', 'item_type':'part',
         'image_url':'/moses/part-image/pds/'+'a'*32+'.webp'},
        {'id':'p2','part_number':'LCN-4040','description':'Surface door closer', 'price':None, 'item_type':'part'},
        {'id':'svc','part_number':'LABOR','description':'Hourly tech rate','price':190,'item_type':'service'},
    ]
    parts_path.write_text(json.dumps({'items': rows}))
    monkeypatch.setattr(pds_data, '_parts_path', lambda _: parts_path)
    return rows, parts_path


def settings(monkeypatch):
    monkeypatch.setenv('PDS_PARTS_STORE_PAYMENTS_ENABLED', 'true')
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_dummy')
    monkeypatch.setenv('PDS_PARTS_STORE_SHIPPING_USD','12.00')
    monkeypatch.setenv('PDS_PARTS_STORE_PUBLIC_ORIGIN','https://pds.example.com')
    monkeypatch.setenv('PDS_PARTS_STORE_STRIPE_WEBHOOK_SECRET','whsec_test_secret')


def checkout_request():
    return store.Cart(lines=[store.Line(id='p1',qty=2)],token=uuid.uuid4())


def fake_stripe(monkeypatch):
    def create(key, record, origin, shipping):
        assert origin == 'https://pds.example.com'
        assert shipping == 1200 and record['subtotal_cents'] == 44000
        fields = store._checkout_payload(record, origin, shipping)
        assert fields['automatic_tax[enabled]'] == 'true'
        assert fields['shipping_address_collection[allowed_countries][0]'] == 'US'
        return {'id':'cs_test_abc','url':'https://checkout.stripe.com/c/pay/cs_test_abc','currency':'usd','mode':'payment'}
    monkeypatch.setattr(store,'_stripe_session',create)


def event(order):
    return {'id': 'evt_test_123', 'type':'checkout.session.completed', 'livemode': False,
            'data':{'object':{'id':'cs_test_abc','client_reference_id':order['id'],
                    'metadata':{'pds_parts_order_id':order['id']},
                    'amount_total':45200,'currency':'usd', 'payment_status':'paid',
                    'customer_details':{'email':'buyer@example.com'},
                    'collected_information':{'shipping_details':{'name':'Test Buyer','address':{'line1':'1 Main St','city':'Anytown','state':'CA','postal_code':'92000','country':'US'}}}}}}


def signed(payload, key='whsec_test_secret'):
    raw=json.dumps(payload).encode()
    t=str(int(time.time()))
    signature=hmac.new(key.encode(),t.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    return raw,f't={t},v1={signature}'


def test_catalog_is_shared_filtered_no_internal_data(tmp_path,monkeypatch):
    rows,path=seed(monkeypatch,tmp_path)
    req=request(tmp_path)
    visible=store.catalog(req)
    assert len(visible['items'])==2
    assert visible['items'][0]['category']=='Exit Devices'
    assert visible['items'][0]['price_cents']==22000
    assert visible['items'][1]['price_cents'] is None
    assert 'supplier' not in visible['items'][0] and 'stock_on_hand' not in visible['items'][0]
    assert visible['items'][0]['image_url']=='/pds-parts/image/p1'
    assert store.catalog(req,q='lcn')['matching']==1
    assert store.catalog(req,category='Door Closers')['matching']==1
    rows[0]['price']='230.00';path.write_text(json.dumps({'items':rows}))
    assert store.catalog(req)['items'][0]['price_cents']==23000  # live master edits appear


def test_public_image_only_catalog_reference(tmp_path,monkeypatch):
    seed(monkeypatch,tmp_path)
    req=request(tmp_path,role=None)
    with pytest.raises(HTTPException) as e:
        store.public_part_image('not-a-part',req)
    assert e.value.status_code==404
    folder=tmp_path/'business_workspaces'/'pds'/'part_images';folder.mkdir(parents=True)
    photo=folder/('a'*32+'.webp');photo.write_bytes(b'RIFFabcdWEBP')
    assert Path(store.public_part_image('p1',req).path) == photo
    with pytest.raises(HTTPException): store.public_part_image('../secret',req)


def test_disabled_checkout_and_unpriced_item(tmp_path,monkeypatch):
    seed(monkeypatch,tmp_path)
    req=request(tmp_path)
    monkeypatch.delenv('PDS_PARTS_STORE_PAYMENTS_ENABLED',raising=False)
    with pytest.raises(HTTPException) as e:store.checkout(req,checkout_request())
    assert e.value.status_code==503
    settings(monkeypatch)
    with pytest.raises(HTTPException) as e:
        store.checkout(req,store.Cart(lines=[store.Line(id='p2',qty=1)],token=uuid.uuid4()))
    assert e.value.status_code==409


def test_checkout_requires_fulfillment_config_and_blocks_live_by_default(tmp_path,monkeypatch):
    seed(monkeypatch,tmp_path);req=request(tmp_path)
    settings(monkeypatch)
    monkeypatch.delenv('PDS_PARTS_STORE_SHIPPING_USD')
    with pytest.raises(HTTPException):store.checkout(req,checkout_request())
    monkeypatch.setenv('PDS_PARTS_STORE_SHIPPING_USD','12.00')
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_live_secret')
    with pytest.raises(HTTPException):store.checkout(req,checkout_request())


def test_successful_test_checkout_idempotent_and_no_pds_mutation(tmp_path,monkeypatch):
    rows,path=seed(monkeypatch,tmp_path);settings(monkeypatch);fake_stripe(monkeypatch)
    req=request(tmp_path);cart=checkout_request()
    response=store.checkout(req,cart)
    assert response['checkout_url'].startswith('https://checkout.stripe.com/')
    again=store.checkout(req,cart)
    assert response==again
    assert json.loads(path.read_text())['items']==rows
    record=store._load(store._orders_path(req))[0]
    assert record['state']=='checkout_pending' and record['lines'][0]['price_cents']==22000
    assert 'supplier_rate' not in str(record)


def test_uncertain_response_fails_closed(tmp_path,monkeypatch):
    seed(monkeypatch,tmp_path);settings(monkeypatch)
    monkeypatch.setattr(store,'_stripe_session',lambda *_: (_ for _ in ()).throw(TimeoutError()))
    req=request(tmp_path);cart=checkout_request()
    with pytest.raises(HTTPException):store.checkout(req,cart)
    assert store._load(store._orders_path(req))[0]['state']=='checkout_uncertain'
    with pytest.raises(HTTPException) as e:store.checkout(req,cart)
    assert e.value.status_code==409


def test_webhook_signature_and_order_reconciliation(tmp_path,monkeypatch):
    import asyncio
    seed(monkeypatch,tmp_path);settings(monkeypatch);fake_stripe(monkeypatch)
    req=request(tmp_path);cart=checkout_request();store.checkout(req,cart)
    row=store._load(store._orders_path(req))[0]
    raw,sig=signed(event(row))
    with pytest.raises(HTTPException):store._signed_event(raw,'t=1,v1=bad','whsec_test_secret')
    assert store._signed_event(raw,sig,'whsec_test_secret')['id']=='evt_test_123'
    async def body():return raw
    req.body=body;req.headers={'stripe-signature':sig}
    done=asyncio.run(store.stripe_webhook(req))
    assert done['processed'] is True
    assert asyncio.run(store.stripe_webhook(req))['duplicate'] is True
    paid=store._load(store._orders_path(req))[0]
    assert paid['state']=='paid' and paid['customer_email']=='buyer@example.com'
    assert paid['shipping_address']['state']=='CA'


def test_webhook_rejects_mismatched_amount(tmp_path,monkeypatch):
    import asyncio
    seed(monkeypatch,tmp_path);settings(monkeypatch);fake_stripe(monkeypatch)
    req=request(tmp_path);store.checkout(req,checkout_request())
    row=store._load(store._orders_path(req))[0]
    bad=event(row);bad['data']['object']['amount_total']=2
    raw,sig=signed(bad)
    async def body():return raw
    req.body=body;req.headers={'stripe-signature':sig}
    with pytest.raises(HTTPException) as err:asyncio.run(store.stripe_webhook(req))
    assert err.value.status_code==409
    assert store._load(store._orders_path(req))[0]['state']=='checkout_pending'


def test_order_permissions(tmp_path,monkeypatch):
    seed(monkeypatch,tmp_path)
    for role,platform in [(None,'pds'),('office','pds'),('office_admin','sdc')]:
        with pytest.raises(HTTPException):store.list_orders(request(tmp_path,role,platform))
    assert store.list_orders(request(tmp_path))['items']==[]


def test_no_stock_or_supplier_cost_leakage_and_no_auto_fulfillment():
    src=Path(store.__file__).read_text()
    assert 'stock_on_hand' not in src
    assert 'supplier_rate' not in src
    assert 'supplier_ordered' in src
    assert 'send_email' not in src
