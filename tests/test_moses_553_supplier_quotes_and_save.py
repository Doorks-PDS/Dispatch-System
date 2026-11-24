"""5.53: PDS supplier RFQ is durable, permissioned and never posts stock/email."""
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from app.routers import pds_supplier_quotes as rfq
from app.routers import data as catalog

ROOT=Path(__file__).resolve().parents[1]


def request(tmp_path, role='office'):
    state=SimpleNamespace(data_dir=str(tmp_path),project_root=str(tmp_path),
        auth_role=role,auth_user={'id':'acct-7','name':'Test Employee'})
    return SimpleNamespace(state=state,app=SimpleNamespace(state=state),session={'active_platform':'pds'})


def supplier(tmp_path):
    folder=tmp_path/'pds_suppliers'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'records.json').write_text(json.dumps([{'id':'supplier1','name':'DCI Door Supply','email':'quotes@dci.example'}]))


def test_supplier_quote_creation_and_lifecycle_are_audited_without_financial_effect(tmp_path):
    supplier(tmp_path)
    req=request(tmp_path,'lead')
    row=rfq.create_quote(rfq.QuoteDraft(supplier_id='supplier1',description='36 x 84 hollow metal door and frame',job_number='1126-15',quantity=2),req)['item']
    assert row['status']=='draft' and row['supplier_email']=='quotes@dci.example'
    assert row['created_by']=='Test Employee'
    assert row['supplier_cost'] is None
    with pytest.raises(HTTPException) as exc:
        rfq.update_quote(row['id'],rfq.QuoteUpdate(status='awaiting_supplier'),req)
    assert exc.value.status_code==422
    sent=rfq.update_quote(row['id'],rfq.QuoteUpdate(status='awaiting_supplier',note='Sent using company email outside Doorks, Nov 24'),req)['item']
    assert sent['history'][-1]['by']=='Test Employee'
    received=rfq.update_quote(row['id'],rfq.QuoteUpdate(status='quote_received',supplier_quote_number='DCI-7722',supplier_cost=920,lead_time='3 weeks'),req)['item']
    assert received['supplier_quote_number']=='DCI-7722'
    ready=rfq.update_quote(row['id'],rfq.QuoteUpdate(status='ready_for_estimate',supplier_quote_number='DCI-7722',supplier_cost=920,note='Office reviewed'),req)['item']
    assert ready['status']=='ready_for_estimate'
    assert len(ready['history'])==4
    assert rfq.list_quotes(req, q='hollow metal')['items'][0]['id']==row['id']
    assert not (tmp_path/'parts_catalog.json').exists()
    assert not (tmp_path/'pds_purchase_orders').exists()
    assert not (tmp_path/'pds_van_stock.json').exists()


def test_supplier_quote_permissions_and_reference_validation(tmp_path):
    supplier(tmp_path)
    with pytest.raises(HTTPException) as exc:
        rfq.create_quote(rfq.QuoteDraft(supplier_id='supplier1',description='Custom storefront'),request(tmp_path,'tech'))
    assert exc.value.status_code==403
    assert rfq.list_quotes(request(tmp_path,'tech'))['items']==[]
    with pytest.raises(HTTPException) as exc:
        rfq.create_quote(rfq.QuoteDraft(supplier_id='nonexistent',description='Custom storefront'),request(tmp_path))
    assert exc.value.status_code==422
    row=rfq.create_quote(rfq.QuoteDraft(supplier_id='supplier1',description='Custom storefront'),request(tmp_path))['item']
    with pytest.raises(HTTPException) as exc:
        rfq.update_quote(row['id'],rfq.QuoteUpdate(status='quote_received',supplier_cost=25),request(tmp_path))
    assert exc.value.status_code==422


def test_quoted_part_reference_does_not_create_inventory(tmp_path,monkeypatch):
    req=request(tmp_path)
    monkeypatch.setattr(catalog,'_pds_stock_balances',lambda req:{})
    part=catalog.create_part(req,catalog.PartPayload(part_number='DCI Quote 7722',description='Hollow metal door + frame',supplier_quote_number='DCI-7722',supplier_quote_id='rfq1',supplier='DCI Door Supply',supplier_rate=920))['item']
    assert part['supplier_quote_number']=='DCI-7722'
    matched=catalog.list_parts(req,q='DCI Quote 7722')['items'][0]
    assert matched['supplier_quote_number']=='DCI-7722' and not matched['stock_recorded']


def test_supplier_quote_ui_and_moses_read_tool_are_connected():
    js=(ROOT/'static/app.js').read_text()
    agent=(ROOT/'app/services/moses_agent.py').read_text()
    assert 'Saving…' in js and "pdsSaveNotice('Saved!'" in js
    assert '📨 Supplier Quotes' in js
    assert 'Mark Sent Externally' in js and 'Copy Request' in js
    assert "opt.value='supplier_quote'" in js and 'pdsQuickSupplierQuoteRequest' in js
    assert 'supplier_quote_number' in js
    assert 'get_pds_supplier_quote_queue' in agent


def test_resend_supplier_quote_requires_approval_and_never_retries_automatically(tmp_path,monkeypatch):
    from app.services import moses_email_transport
    supplier(tmp_path)
    req=request(tmp_path,'office')
    row=rfq.create_quote(rfq.QuoteDraft(supplier_id='supplier1',description='Storefront 2-pane door'),req)['item']
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setattr(moses_email_transport,'ready',lambda sender: None)
    submitted=[]
    def accepted(message):
        submitted.append(message)
        return 'abc_message_123'
    monkeypatch.setattr(moses_email_transport,'send_resend',accepted)
    with pytest.raises(HTTPException) as exc:
        rfq.send_supplier_request(row['id'],rfq.SendDecision(approve=False),req)
    assert exc.value.status_code==422 and not submitted
    result=rfq.send_supplier_request(row['id'],rfq.SendDecision(approve=True),req)
    assert result['state']=='accepted_by_provider'
    assert result['item']['sent_via']=='resend'
    assert result['item']['delivery_status']=='accepted_by_provider'
    assert submitted[0]['to']=='quotes@dci.example'
    assert submitted[0]['reply_to']=='reception@prioritydoors.com'
    with pytest.raises(HTTPException) as exc:
        rfq.send_supplier_request(row['id'],rfq.SendDecision(approve=True),req)
    assert exc.value.status_code==409 and len(submitted)==1
    another=rfq.create_quote(rfq.QuoteDraft(supplier_id='supplier1',description='Fire rated door'),req)['item']
    def failed(_): raise TimeoutError('Simulated lost response')
    monkeypatch.setattr(moses_email_transport,'send_resend',failed)
    uncertain=rfq.send_supplier_request(another['id'],rfq.SendDecision(approve=True),req)
    assert uncertain['state']=='uncertain' and uncertain['sent'] is False
    assert rfq.list_quotes(req,q='Fire rated door')['items'][0]['status']=='send_uncertain'
    with pytest.raises(HTTPException) as exc:
        rfq.send_supplier_request(another['id'],rfq.SendDecision(approve=True),req)
    assert exc.value.status_code==409
