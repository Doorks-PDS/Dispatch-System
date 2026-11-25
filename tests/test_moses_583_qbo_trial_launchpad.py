"""5.83 trial packet never calls provider transaction writes or posts fees."""
from types import SimpleNamespace
from unittest.mock import Mock
import json
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services import pds_qbo_trial_packet as packets


def _mock_base(monkeypatch, kind='invoice', connected=True, mapped=True, subtotal='100.00'):
    doc = {
        'kind': kind, 'pds_number': 'JS00042' if kind == 'invoice' else 'PO-00042',
        'source_fingerprint': 'e'*64, 'subtotal': subtotal, 'total': '107.75', 'tax': '7.75',
        'date': '2026-11-24', 'lines': [{'position':1, 'quantity':'2',
                                        'unit_price':'50.00', 'unit_cost':'50.00',
                                        'amount':'100.00', 'description':'Door service'}],
    }
    monkeypatch.setattr(packets.qb, '_admin', lambda request: None)
    monkeypatch.setattr(packets.preview, 'preview_invoice', lambda request, number: doc)
    monkeypatch.setattr(packets.preview, 'preview_supplier_po', lambda request, number: doc)
    monkeypatch.setattr(packets.trial, 'report', lambda request, kind, number: {'checks':[{'code':'tax','passed':False}]})
    monkeypatch.setattr(packets.numbering, 'get_plan', lambda request: {
        'saved':True, 'policies': {'invoice':'request_doorks_number',
                                  'supplier_po':'quickbooks_assigns_number'}})
    monkeypatch.setattr(packets.connection, '_environment', lambda: 'sandbox')
    monkeypatch.setattr(packets.connection, 'configuration', lambda request: {
        'edition':'online', 'authorized':connected, 'company_id':'111',
        'company_name':'Sandbox PDS', 'environment':'sandbox',
        'last_read_only_verification':packets.time.time() if connected else None,
        'checks': {'client_id_present':True}})
    monkeypatch.setattr(packets.sync, 'readiness', lambda request, kind, number: {
        'party_match':{'status':'approved_master_link', 'provider_id':'55'} if mapped else {'status':'missing'},
    })
    monkeypatch.setattr(packets.line_mapper, 'status', lambda request, kind, number: {
        'all_lines_reviewed':mapped, 'mapped_lines':int(mapped), 'total_lines':1,
        'lines':[{'status':'approved' if mapped else 'needs_review',
                  'provider_id':'77' if mapped else None}]
    })
    return doc


def test_invoice_packet_has_correct_review_shape_but_never_authorizes_post(monkeypatch):
    _mock_base(monkeypatch)
    never=Mock(side_effect=AssertionError('unexpected provider duplicate call'))
    monkeypatch.setattr(packets.collisions, 'check', never)
    result=packets.packet(object(), 'invoice', 'JS00042')
    assert result['source_amounts']['amount_check']['passed'] is True
    assert result['provider_shape_draft']['CustomerRef']['value']=='55'
    assert result['provider_shape_draft']['DocNumber']=='JS00042'
    assert result['provider_shape_draft']['Line'][0]['SalesItemLineDetail']['ItemRef']['value']=='77'
    assert 'TxnTaxDetail' not in result['provider_shape_draft']
    assert 'SalesTermRef' not in result['provider_shape_draft']
    assert result['can_post'] is False and result['provider_write_performed'] is False
    assert result['draft_is_safe_to_post'] is False
    assert result['payment_link_enabled'] is False
    assert never.call_count == 0


def test_po_packet_has_purchase_detail_and_respects_number_policy(monkeypatch):
    _mock_base(monkeypatch, kind='supplier_po')
    result=packets.packet(object(), 'supplier_po', 'PO-00042')
    draft=result['provider_shape_draft']
    assert draft['VendorRef']['value']=='55'
    assert 'DocNumber' not in draft
    assert draft['Line'][0]['DetailType']=='ItemBasedExpenseLineDetail'
    assert draft['Line'][0]['ItemBasedExpenseLineDetail']['ItemRef']['value']=='77'


def test_disconnected_packet_does_not_query_provider_or_guess_ids(monkeypatch):
    _mock_base(monkeypatch, connected=False)
    never=Mock(side_effect=AssertionError('must not load linked provider data'))
    monkeypatch.setattr(packets.sync, 'readiness', never)
    monkeypatch.setattr(packets.line_mapper, 'status', never)
    monkeypatch.setattr(packets.collisions, 'check', never)
    result=packets.packet(object(), 'invoice', 'JS00042', check_duplicates=True)
    assert result['provider_shape_draft'] is None
    assert result['can_post'] is False
    assert never.call_count == 0
    assert any('Authorize' in msg for msg in result['blockers'])


def test_unmatched_party_or_items_prevents_draft(monkeypatch):
    _mock_base(monkeypatch, mapped=False)
    result=packets.packet(object(), 'invoice', 'JS00042')
    assert result['provider_shape_draft'] is None
    assert result['mapped_lines']==0
    assert any('Approve' in msg for msg in result['blockers'])


def test_wrong_subtotal_blocks_draft_but_reports_failure(monkeypatch):
    _mock_base(monkeypatch, subtotal='95.00')
    result=packets.packet(object(), 'invoice', 'JS00042')
    assert not result['source_amounts']['amount_check']['passed']
    assert result['provider_shape_draft'] is None


def test_expired_company_verification_blocks_review(monkeypatch):
    _mock_base(monkeypatch)
    monkeypatch.setattr(packets.connection, 'configuration', lambda request: {
        'edition':'online', 'authorized':True, 'company_id':'111', 'company_name':'Sandbox PDS',
        'environment':'sandbox', 'last_read_only_verification':packets.time.time() - 86401})
    never=Mock(side_effect=AssertionError('stale company must not reuse mappings'))
    monkeypatch.setattr(packets.sync, 'readiness', never)
    result=packets.packet(object(), 'invoice', 'JS00042')
    assert not result['recently_verified'] and result['provider_shape_draft'] is None
    assert never.call_count==0


def test_collision_is_flagged_and_does_not_authorize_sync(monkeypatch):
    _mock_base(monkeypatch)
    monkeypatch.setattr(packets.collisions, 'check', lambda request, kind, number: {
        'collision_found': True, 'match_count': 1, 'matches':[{'id':'123', 'doc_number':number}]})
    result=packets.packet(object(), 'invoice', 'JS00042', check_duplicates=True)
    assert result['duplicate_check']['collision_found'] is True
    assert any('collision' in item.lower() for item in result['blockers'])
    assert result['can_post'] is False


def test_setup_diagnostics_has_no_secret_values(monkeypatch):
    _mock_base(monkeypatch)
    result=packets.setup_diagnostics(object())
    dumped=json.dumps(result)
    assert result['provider_write_performed'] is False
    assert 'PDS_QBO_CLIENT_SECRET' in dumped
    assert 'raw_token' not in dumped
    assert 'pds-quickbooks/oauth/callback' in dumped


def test_unknown_kind_fails_before_provider(monkeypatch):
    _mock_base(monkeypatch)
    with pytest.raises(HTTPException) as e:
        packets.packet(object(), 'payment', 'JS00042')
    assert e.value.status_code==422


def test_ui_launchpad_and_safe_routes_are_available():
    root=Path(__file__).resolve().parents[1]
    ui=(root/'static/app.js').read_text()
    routes=(root/'app/routers/pds_quickbooks_bridge.py').read_text()
    assert 'qbhPacketPreview' in ui and 'qbhPacketDownload' in ui
    assert "window.location.href='/pds-quickbooks/trial-packet/'" in ui
    assert "@router.get('/trial-packet/{kind}/{number}/download')" in routes
    assert 'Cache-Control' in routes and 'no-store' in routes


def test_master_link_coverage_tracks_each_pds_record_type(monkeypatch):
    from app.services import pds_qbo_master_links as master
    _mock_base(monkeypatch)
    monkeypatch.setattr(master, '_company', lambda request: ('111','sandbox','fake-token'))
    monkeypatch.setattr(master, '_path', lambda request: 'unused-local-link-ledger.json')
    monkeypatch.setattr(packets.qb, '_load', lambda path: {'items': {
        'customers:c1': {'company_id':'111','environment':'sandbox','source_name':'Cheesecake Factory','provider_id':'8'},
        'suppliers:s1': {'company_id':'111','environment':'sandbox','source_name':'Old Vendor Name','provider_id':'9'},
    }})
    monkeypatch.setattr(master, '_sources', lambda request, kind: {
        'customers':[{'pds_id':'c1','name':'Cheesecake Factory'}],
        'vendors':[{'pds_id':'v1','name':'Automatic Door Techs'}],
        'suppliers':[{'pds_id':'s1','name':'Door Parts Supplier'}],
        'items':[{'pds_id':'i1','name':'Part A'}],
    }[kind])
    out=packets.mapping_coverage(object())
    assert out['counts']['customers']['approved_local_links']==1
    assert out['counts']['vendors']['unlinked']==1
    assert out['counts']['suppliers']['stale_or_wrong_company']==1
    assert out['provider_writes'] is False and out['provider_records_queried'] is False
