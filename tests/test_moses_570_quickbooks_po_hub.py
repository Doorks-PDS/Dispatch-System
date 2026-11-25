"""5.70: supplier PO handoff and Office Admin-only QuickBooks dashboard."""
import json
from pathlib import Path
from fastapi import HTTPException
import pytest
from app.services import pds_quickbooks_purchase_orders as po
from app.services import pds_quickbooks_bridge as qb
from app.routers import pds_quickbooks_bridge as route
from test_moses_567_quickbooks_handoff import setup_request

ROOT = Path(__file__).parents[1]


def fixture(tmp_path, role='office_admin'):
    req, _ = setup_request(tmp_path, role)
    job = {'id': 'jobA', 'job_number': '1126-20', 'customer': 'Test PDS Customer'}
    req.app.state.calendar_store.list_jobs = lambda: [job]
    folder = tmp_path / 'pds_purchase_orders'
    folder.mkdir()
    item = {
        'id': 'poA', 'po_number': 'PO-00020', 'vendor': 'Test Parts Supply', 'supplier_id': 'vendorA',
        'job_id': 'jobA', 'work_order': '1126-20', 'customer': job['customer'],
        'date': '2026-11-24', 'status': 'Ordered', 'tax': '5.00', 'shipping': '12.00',
        'total': '217.00', 'line_items': json.dumps([
            {'item': 'DC-1', 'description': 'Door closer', 'quantity': 2, 'rate': 100},
        ]),
    }
    (folder / 'records.json').write_text(json.dumps([item]))
    return req, item, folder / 'records.json'


def test_prepares_po_only_after_review_and_idempotent(tmp_path):
    req, row, _ = fixture(tmp_path)
    data = po.preview(req)
    assert data['ready_count'] == 1
    assert data['connected_to_quickbooks'] is False
    assert data['automatic_sync_enabled'] is False
    ready = data['purchase_orders'][0]
    assert ready['ready'] and ready['number'] == 'PO-00020'
    assert ready['total'] == '217.00' and ready['tax'] == '5.00'
    result = po.prepare(req, ready['number'], ready['fingerprint'])
    assert result['state'] == 'prepared_for_review' and result['pushed_to_quickbooks'] is False
    assert po.prepare(req, ready['number'], ready['fingerprint'])['duplicate'] is True
    assert 'PO-00020' in po.export_review_csv(req)
    assert po.preview(req)['prepared_count'] == 1
    assert not (tmp_path / 'pds_quickbooks_invoice_handoff.json').exists()
    assert row['status'] == 'Ordered'


def test_order_without_email_may_be_prepared(tmp_path):
    req, _, _ = fixture(tmp_path)
    assert not (tmp_path / 'moses_po_delivery_actions.json').exists()
    ready = po.preview(req)['purchase_orders'][0]
    assert ready['ready']


def test_no_customer_po_changes_or_inventory_updates(tmp_path):
    req, row, src = fixture(tmp_path)
    req.app.state.calendar_store.list_jobs = lambda: [{'id': 'jobA','job_number': '1126-20',
                                                     'customer': 'Test PDS Customer', 'po_number': 'CUSTOMER-123'}]
    before = src.read_bytes()
    ready = po.preview(req)['purchase_orders'][0]
    po.prepare(req, ready['number'], ready['fingerprint'])
    assert src.read_bytes() == before
    assert req.app.state.calendar_store.list_jobs()[0]['po_number'] == 'CUSTOMER-123'
    assert not (tmp_path/'pds_inventory').exists()


@pytest.mark.parametrize('role', ['office', 'tech', 'lead', 'guest', 'admin', ''])
def test_all_purchase_order_endpoints_admin_only(tmp_path, role):
    req, _, _ = fixture(tmp_path,role)
    for action in [lambda: po.preview(req),lambda: po.export_review_csv(req),
                   lambda: po.prepare(req, 'PO-00020','a'*64),
                   lambda: route.purchase_orders(req),lambda: route.po_review_csv(req),
                   lambda: route.prepare_po(route.PreparePORequest(po_number='PO-00020',fingerprint='a'*64,confirm=True),req)]:
        with pytest.raises(HTTPException) as error:action()
        assert error.value.status_code == 403


def test_must_confirm_and_match_reviewed_fingerprint(tmp_path):
    req, _, _ = fixture(tmp_path)
    ready = po.preview(req)['purchase_orders'][0]
    with pytest.raises(HTTPException) as error:
        route.prepare_po(route.PreparePORequest(po_number='PO-00020',fingerprint=ready['fingerprint'],confirm=False),req)
    assert error.value.status_code == 422
    with pytest.raises(HTTPException) as error:po.prepare(req,ready['number'],'0'*64)
    assert error.value.status_code == 409
    assert not (tmp_path/'pds_quickbooks_po_handoff.json').exists()


@pytest.mark.parametrize('change', [
    {'status': 'Draft'}, {'status': 'Cancelled'}, {'vendor': ''},
    {'job_id': 'wrong'}, {'customer': 'Different company'},
    {'total': '200'}, {'line_items': 'not json'},
    {'line_items': '[{"item":"closer","quantity":1,"rate":-5}]'},
])
def test_draft_unlinked_mismatch_invalid_po_not_preparable(tmp_path, change):
    req, record, path = fixture(tmp_path)
    record.update(change);path.write_text(json.dumps([record]))
    data = po.preview(req)['purchase_orders'][0]
    assert not data['ready']
    with pytest.raises(HTTPException) as error:po.prepare(req,data['number'],data['fingerprint'])
    assert error.value.status_code == 409


def test_changed_po_is_flagged_and_requires_reconciliation(tmp_path):
    req, record, path = fixture(tmp_path)
    ready = po.preview(req)['purchase_orders'][0]
    po.prepare(req, ready['number'], ready['fingerprint'])
    record['status'] = 'Shipped'
    path.write_text(json.dumps([record]))
    updated = po.preview(req)['purchase_orders'][0]
    assert updated['handoff_status']=='changed_since_preparation'
    assert not updated['ready']
    with pytest.raises(HTTPException) as e:po.prepare(req,updated['number'],updated['fingerprint'])
    assert e.value.status_code == 409
    assert po.export_review_csv(req).count('PO-00020') == 0


def test_duplicate_number_fails_closed(tmp_path):
    req, record, path = fixture(tmp_path)
    records = [record,dict(record,id='duplicate')]
    path.write_text(json.dumps(records))
    with pytest.raises(HTTPException) as error:po.preview(req)
    assert error.value.status_code==409


def test_csv_formula_safety(tmp_path):
    req,record,path = fixture(tmp_path)
    record['vendor'] = '=HYPERLINK("evil")'
    path.write_text(json.dumps([record]))
    row=po.preview(req)['purchase_orders'][0]
    po.prepare(req,row['number'],row['fingerprint'])
    assert "'=HYPERLINK" in po.export_review_csv(req)


def test_po_requires_workspace_and_edition_does_not_authorize_sync(tmp_path):
    req,_,_ = fixture(tmp_path)
    req.session['active_platform']='doorks'
    with pytest.raises(HTTPException) as e:po.preview(req)
    assert e.value.status_code == 403
    req.session['active_platform']='pds'
    qb.select_edition(req,'online')
    assert po.preview(req)['connected_to_quickbooks'] is False


def test_quickbooks_hub_has_po_tab_and_no_auto_sync_buttons():
    app=(ROOT/'static/app.js').read_text()
    css=(ROOT/'static/pds_quickbooks_hub.css').read_text()
    router=(ROOT/'app/routers/pds_quickbooks_bridge.py').read_text()
    assert 'Supplier POs' in app
    for token in ['/pds-quickbooks/purchase-orders','/pds-quickbooks/prepare-po','/pds-quickbooks/po-review.csv',
                  'Handoff activity','Connection setup','Invoice handoff','Export review CSV']:
        assert token in app
    assert 'role !== \'office_admin\'' in app
    assert 'class="qbh-workflow"' in app
    assert '@media(max-width:610px)' in css
    assert "@router.get('/purchase-orders')" in router
    assert 'transaction' in app.lower()


def test_prepared_invoice_changed_is_not_still_shown_ready(tmp_path):
    from test_moses_567_quickbooks_handoff import mark_sent
    req, doc = setup_request(tmp_path)
    mark_sent(req)
    initial = qb.preview(req)['invoices'][0]
    qb.prepare(req, initial['number'], initial['fingerprint'])
    doc['items'][0]['rate'] = 123
    changed = qb.preview(req)['invoices'][0]
    assert changed['handoff_status'] == 'changed_since_preparation'
    assert not changed['ready']
    assert 'reconcile' in changed['needs_review'][-1]
