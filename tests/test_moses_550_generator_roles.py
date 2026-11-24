"""PDS 5.50: technician invoices, guarded PO option, and compact document generator.

Tests source and authorization without touching production data or providers.
"""
from pathlib import Path
from types import SimpleNamespace
import asyncio
import pytest
from fastapi import HTTPException

from app.routers import documents, document_vault as vault
from app.services import moses_pds_document_email as email_service

ROOT = Path(__file__).resolve().parents[1]


def signed(role, tmp_path):
    return SimpleNamespace(
        state=SimpleNamespace(auth_user={'id':'user-1','name':'Employee','username':'employee'},auth_role=role),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path,require_key=lambda key,request=None:role)),
    )


def test_technician_can_create_and_edit_estimates_and_invoices_but_never_purchase_orders(tmp_path):
    req=signed('tech',tmp_path)
    for kind in ('estimate','invoice'):
        for action in ('create','edit'):
            assert documents._document_permission(req,None,kind,action)=='tech'
        with pytest.raises(HTTPException) as exc:
            documents._document_permission(req,None,kind,'delete')
        assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        documents._document_permission(req,None,'purchase_order','create')
    assert exc.value.status_code==403
    email_service._guard(req,'invoice')
    email_service._guard(req,'estimate')
    with pytest.raises(HTTPException):email_service._guard(req,'purchase_order')


def test_technician_sees_native_invoice_and_estimate_but_no_other_docs(tmp_path):
    req=signed('tech',tmp_path)
    req.app.state.documents_store=SimpleNamespace(list_documents=lambda **kwargs:[
        {'type':'estimate','number':'RE00001','filename':'RE00001.pdf'},
        {'type':'invoice','number':'JS00001','filename':'JS00001.pdf'},
        {'type':'purchase_order','number':'PO-1','filename':'PO-1.pdf'}])
    rows=documents.list_documents(req,job_id='',type='',x_api_key=None)['items']
    assert {r['type'] for r in rows}=={'estimate','invoice'}


def test_technician_may_upload_external_invoice_without_gaining_po(tmp_path):
    req=signed('tech',tmp_path)
    saved=asyncio.run(vault.create('pds',req,document_type='invoice',notes='QB Invoice 510',
        vendor='',document_number='QB-510',document_date='',po_number='',job_number='1126-15',extracted_json='',
        library_scope='business',file=None))['item']
    assert saved['document_type']=='invoice'
    assert saved['source']=='external'
    rows=vault.listing('pds',req,library_scope='business')['items']
    assert len(rows)==1 and rows[0]['document_number']=='QB-510'
    with pytest.raises(HTTPException) as exc:
        asyncio.run(vault.create('pds',req,document_type='purchase_order',notes='Unauthorized',vendor='',
            document_number='',document_date='',po_number='',job_number='',extracted_json='',library_scope='business',file=None))
    assert exc.value.status_code==403


def test_compact_generator_does_not_use_duplicate_charge_button_bank():
    js=(ROOT/'static/app.js').read_text()
    css=(ROOT/'static/style.css').read_text()
    assert '<option value="invoice">Invoice</option>${canCreatePdsPO ?' in js
    assert "dom.type.value === 'purchase_order'" in js
    assert "renderUnifiedPurchaseOrders('pds', true" in js
    assert "document.getElementById('newDocumentKind')" in js
    assert 'function enteredDocItems()' in js
    assert 'function suggestForDescription' in js
    assert '🚗' in js and '⛽' in js
    assert 'id="doc_auto_fill"' in js and 'id="doc_source_form"' in js
    for old in ('id="add_trip"','id="add_fuel"','id="add_freight"','id="add_single"','id="add_crew"'):
        assert old not in js
    assert '.pds-doc-suggestion' in css
    assert "['tech','lead','office','office_admin','admin']" in js
