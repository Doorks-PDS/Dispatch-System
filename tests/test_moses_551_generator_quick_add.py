"""5.51 cumulative quick-create, billing defaults, and non-stock service safeguards.

Tests exercise real catalog and PO routes with isolated temporary data only.
"""
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.routers import data, pds_purchase_orders as orders

ROOT=Path(__file__).resolve().parents[1]


def request(tmp_path, role='lead'):
    state=SimpleNamespace(project_root=tmp_path,data_dir=tmp_path,auth_user={'id':'worker-1','name':'Lead One'},auth_role=role)
    return SimpleNamespace(app=SimpleNamespace(state=state),state=state,session={'active_platform':'pds'})


def test_service_catalog_is_saved_and_never_becomes_warehouse_stock(tmp_path, monkeypatch):
    monkeypatch.setattr(data, '_parts_path', lambda r:tmp_path/'parts_catalog.json')
    service=data.create_part(request(tmp_path), data.PartPayload(
        item_type='service',part_number='SUB-GLASS',description='Subcontractor glazing',price=250,supplier='Glazing vendor'),None)['item']
    assert service['item_type']=='service'
    rows=data.list_parts(request(tmp_path),None)['items']
    assert len(rows)==1 and rows[0]['item_type']=='service'
    assert rows[0]['stock_recorded'] is False
    with pytest.raises(HTTPException) as error:
        data.adjust_pds_part_stock(service['id'],data.PdsStockAdjustment(delta=1,reason='Test adjustment'),request(tmp_path,'office'))
    assert error.value.status_code==400
    with pytest.raises(HTTPException) as error:
        data.create_part(request(tmp_path),data.PartPayload(item_type='service',part_number='SUB2',min_stock=1),None)
    assert error.value.status_code==400
    from app.routers import pds_van_stock
    assert service['id'] not in pds_van_stock._parts(request(tmp_path))


def test_standard_part_retains_legacy_part_type(tmp_path,monkeypatch):
    monkeypatch.setattr(data,'_parts_path',lambda r:tmp_path/'parts_catalog.json')
    obj=data.create_part(request(tmp_path),data.PartPayload(part_number='311S',description='Closer'),None)['item']
    assert obj['item_type']=='part'
    assert data.list_parts(request(tmp_path),None)['items'][0]['item_type']=='part'
    with pytest.raises(HTTPException) as error:
        data.update_part(request(tmp_path),obj['id'],data.PartPayload(item_type='service',part_number='311S',description='Closer'),None)
    assert error.value.status_code==409


def test_lead_can_create_supplier_but_cannot_change_existing_supplier(tmp_path):
    r=request(tmp_path,'lead')
    obj=orders.create_supplier(orders.POInput(data={'name':'Glazing Sub','contact':'Alex','email':'alex@example.com','address':'Test address'}),r)['item']
    assert obj['name']=='Glazing Sub'
    assert len(orders.list_suppliers(r)['items'])==1
    with pytest.raises(HTTPException) as error:
        orders.update_supplier(obj['id'],orders.POInput(data={'name':'Different'}),r)
    assert error.value.status_code==403
    with pytest.raises(HTTPException) as error:
        orders.create_supplier(orders.POInput(data={'name':'Glazing Sub'}),r)
    assert error.value.status_code==409
    with pytest.raises(HTTPException) as error:
        orders.create_supplier(orders.POInput(data={'name':'Technician Supplier'}),request(tmp_path,'tech'))
    assert error.value.status_code==403


def test_generator_has_inline_customer_vendor_catalog_and_review_before_save():
    source=(ROOT/'static/app.js').read_text()
    assert 'function pdsQuickCustomerEditor' in source
    assert 'function pdsQuickCatalogEditor' in source
    assert 'pdsQuickRecordEditor' in source
    assert "id=\"doc_new_customer\"" in source
    assert "textContent='＋ Add Vendor'" in source
    assert 'id="part_lookup_new"' in source and '＋ New' in source
    assert 'Apply Selected Suggestions' in source
    assert 'Apply Checked Fields' in source
    assert 'defaultDocItems(pricing)' in source
    assert 'Number(pricing.trip ?? 190)' in source
    assert "part.item_type==='service'?'service':'part'" in source
    assert "p.item_type!=='service'" in source


def test_saved_pricing_store_trip_190_is_not_reset():
    from app.services.pricing_store import DEFAULTS
    assert DEFAULTS['trip']==190
    js=(ROOT/'static/app.js').read_text()
    assert 'code: "TRIP", description: "Trip Charge", qty: 1, rate: Number(pricing.trip ?? 190)' in js
