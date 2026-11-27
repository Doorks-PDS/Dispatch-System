"""5.95: core reviews are inquiry-only, never Stripe or shopping cart."""
import json
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.routers import pds_parts_store as store
from tests.test_pds_parts_store_592 import request, seed, settings

ROOT = Path(__file__).resolve().parents[1]


def add_parts(monkeypatch, tmp_path):
    rows, path = seed(monkeypatch, tmp_path)
    rows.extend([
        {'id':'ctrl','description':'NABCO automatic sliding door controller','part_number':'GT-22-C','manufacturer':'NABCO','price':'890.00'},
        {'id':'motor','description':'Door motor and drive assembly','part_number':'DR-22','price':'460.00'},
        {'id':'sensor','description':'Automatic swing door presence sensor','part_number':'PR-7','price':'120.00'},
        {'id':'core','description':'Specialized retrofit assembly','part_number':'RR-7','price':'235.00','core_return_required':True,'core_charge':'85.00'},
        {'id':'manual','description':'Commercial door weatherstrip','part_number':'W-88','price':'19.00','store_inquiry_only':True},
        {'id':'board','description':'Automatic door control board','part_number':'CTRL-BOARD','price':''},
        {'id':'micro','description':'Custom mounting bracket','part_number':'CORE-MICRO','price':'79.00','core_charge':'0.25'},
        {'id':'legacy','description':'Replacement hinge set','part_number':'CORE-LEGACY','price':'79.00','core_charge':'unknown'},
    ])
    path.write_text(json.dumps({'items':rows}))
    return rows,path


def test_auto_components_and_core_parts_show_prices_but_are_inquiry_only(monkeypatch,tmp_path):
    add_parts(monkeypatch,tmp_path)
    items={p['id']:p for p in store.catalog(request(tmp_path,role=None))['items']}
    assert items['p1']['inquiry_only'] is False
    for id in ('ctrl','motor','sensor','core','manual','board','micro','legacy'):
        assert items[id]['inquiry_only'] is True
    assert items['ctrl']['price_cents']==89000
    assert items['core']['core_review'] is True
    assert items['board']['price_cents'] is None
    for p in items.values():
        assert 'core_charge' not in p and 'supplier_rate' not in p
    assert store.catalog(request(tmp_path),category='Automatic Doors')['matching']>=3


def test_auto_cannot_checkout_even_when_sandbox_enabled(monkeypatch,tmp_path):
    add_parts(monkeypatch,tmp_path);settings(monkeypatch)
    req=request(tmp_path,role=None)
    for id in ('ctrl','motor','sensor','core','manual','micro','legacy'):
        data=store.Cart(lines=[store.Line(id=id,qty=2)],token=uuid.uuid4())
        with pytest.raises(HTTPException) as e:store.cart_quote(req,data)
        assert e.value.status_code==409
        with pytest.raises(HTTPException) as e:store.checkout(req,data)
        assert e.value.status_code==409
        payload=store.OrderRequest(lines=data.lines,token=uuid.uuid4(),name='Customer',email='test@example.com')
        with pytest.raises(HTTPException) as e:store.request_order(req,payload)
        assert e.value.status_code==409
    assert not store._orders_path(req).exists()


def test_inquiry_captures_contact_without_payment_and_sdc_can_track(monkeypatch,tmp_path):
    rows,path=add_parts(monkeypatch,tmp_path)
    req=request(tmp_path,role=None)
    data=store.PartInquiry(part_id='ctrl',qty=2,token=uuid.uuid4(),name='Morgan Buyer',email='Morgan@Example.com',phone='555-1200',note='Need controller')
    first=store.part_inquiry(req,data)
    assert first['payment_received'] is False
    assert first['core_review_required'] is True
    assert store.part_inquiry(req,data)['duplicate'] is True
    record=store._load(store._orders_path(req))[0]
    assert record['kind']=='part_inquiry' and record['state']=='needs_quote'
    assert record['paid_at'] is None and record['subtotal_cents'] is None
    assert record['customer_price_estimate_cents']==178000
    assert record['customer_email']=='morgan@example.com'
    assert record['core_review_required'] is True
    assert record['core_return_status']=='unconfirmed'
    assert record['core_estimate_cents'] is None
    assert json.loads(path.read_text())['items']==rows
    with pytest.raises(HTTPException):store.sdc_order_report(req)
    sdc=request(tmp_path,role='office_admin',platform='sdc')
    assert store.sdc_order_report(sdc)['items'][0]['state']=='needs_quote'
    result=store.sdc_update_order(record['id'],store.OrderUpdate(status='contacted',staff_notes='Core confirmed by phone'),sdc)
    assert result['status']=='contacted' and result['paid'] is False
    with pytest.raises(HTTPException) as err:
        store.sdc_update_order(record['id'],store.OrderUpdate(status='shipped'),sdc)
    assert err.value.status_code==409


def test_unpriced_auto_part_inquiry_and_token_reuse(monkeypatch,tmp_path):
    add_parts(monkeypatch,tmp_path);req=request(tmp_path,role=None)
    data=store.PartInquiry(part_id='board',qty=1,token=uuid.uuid4(),name='Test Buyer',email='test@example.com')
    store.part_inquiry(req,data)
    record=store._load(store._orders_path(req))[0]
    assert record['lines'][0]['price_cents'] is None
    assert record['customer_price_estimate_cents'] is None
    with pytest.raises(HTTPException) as e:
        store.part_inquiry(req,data.model_copy(update={'part_id':'ctrl'}))
    assert e.value.status_code==409


def test_inquiry_is_immutable_to_anonymous_status_changes(monkeypatch,tmp_path):
    add_parts(monkeypatch,tmp_path)
    req=request(tmp_path,role=None)
    data=store.PartInquiry(part_id='ctrl',qty=1,token=uuid.uuid4(),name='A Buyer',email='a@example.com')
    store.part_inquiry(req,data)
    record=store._load(store._orders_path(req))[0]
    with pytest.raises(HTTPException):
        store.update_order(record['id'],store.OrderUpdate(status='contacted'),req)


def test_frontend_and_sales_have_inquiry_controls():
    html=(ROOT/'static/pds_parts_store.html').read_text()
    report=(ROOT/'static/sdc_sales_reports.html').read_text()
    for mark in ('inquiryModal','inquiryQty','inquiryName','inquiryEmail','inquiryPhone',
                 '/pds-parts/api/part-inquiries','canCart(p)','p.inquiry_only'):
        assert mark in html
    for mark in ("partsQuotes", "needs_quote", "CORE / SPECIALTY INQUIRY", "Core return / charge needs confirmation"):
        assert mark in report
