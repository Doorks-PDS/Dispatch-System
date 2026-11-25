"""5.71: stable PDS numbers, Intuit-numbering plan and nonduplicating verified links."""
import json
from pathlib import Path
from fastapi import HTTPException
import pytest

from app.services import pds_quickbooks_numbering as numbering
from app.routers import pds_quickbooks_bridge as route
from test_moses_567_quickbooks_handoff import setup_request
from test_moses_570_quickbooks_po_hub import fixture as po_fixture

ROOT = Path(__file__).parents[1]


def test_default_numbers_remain_unchanged_and_dry_run_only(tmp_path):
    request, doc = setup_request(tmp_path)
    result = route.numbering(request)
    assert result['saved'] is False
    assert result['policies'] == {x: 'request_doorks_number' for x in numbering.KINDS}
    assert [row['doorks_example'] for row in result['examples']] == ['RE00097', 'JS00021', 'PO-00020']
    assert result['quickbooks_numbering_preferences_verified'] is False
    assert result['connected_to_quickbooks'] is False
    assert result['changes_local_numbers'] is False
    assert doc['number'] == 'JS00021'
    assert not (tmp_path / 'pds_quickbooks_numbering.json').exists()
    assert not (tmp_path / 'pds_quickbooks_verified_refs.json').exists()


def test_save_policies_with_explicit_approval_does_not_touch_invoice(tmp_path):
    request, doc = setup_request(tmp_path)
    pol = {'estimate': 'request_doorks_number', 'invoice': 'quickbooks_assigns_number',
           'supplier_po': 'request_doorks_number'}
    with pytest.raises(HTTPException) as ex:
        route.save_numbering(route.NumberPlan(policies=pol, confirm=False), request)
    assert ex.value.status_code == 422
    result = route.save_numbering(route.NumberPlan(policies=pol, confirm=True), request)
    assert result['saved'] is True
    assert result['policies'] == pol
    assert result['examples'][1]['quickbooks_number_not_assigned'] is True
    assert result['examples'][1]['quickbooks_example'] is None
    assert doc['number'] == 'JS00021'
    assert not (tmp_path / 'pds_quickbooks_invoice_handoff.json').exists()
    assert not (tmp_path / 'pds_quickbooks_verified_refs.json').exists()
    assert json.loads((tmp_path / 'pds_quickbooks_numbering.json').read_text())['policies'] == pol


@pytest.mark.parametrize('role', ['tech', 'lead', 'office', 'guest'])
def test_restricted_to_office_admin_read_and_write(tmp_path, role):
    request, _ = setup_request(tmp_path, role)
    for operation in (lambda: route.numbering(request),
                      lambda: route.save_numbering(route.NumberPlan(policies={k:'request_doorks_number'
                                                                           for k in numbering.KINDS},confirm=True), request),
                      lambda: numbering.verified_reference(request, kind='invoice',
                                                            doorks_number='JS00021', company_id='abc',
                                                            quickbooks_id='q1', quickbooks_number='17566',
                                                            checked_against_provider=True)):
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403


def test_wrong_workspace_cannot_access_numbering(tmp_path):
    request, _ = setup_request(tmp_path)
    request.session['active_platform'] = 'doorks'
    with pytest.raises(HTTPException) as ex:
        route.numbering(request)
    assert ex.value.status_code == 403


def test_reject_partial_invalid_or_corrupt_plan(tmp_path):
    request, _ = setup_request(tmp_path)
    for pol in ({'invoice': 'request_doorks_number'},
                {x: 'bad' for x in numbering.KINDS},
                {**{x:'request_doorks_number' for x in numbering.KINDS}, 'po_number': 'bad'}):
        with pytest.raises(HTTPException) as ex:
            numbering.save_plan(request, pol)
        assert ex.value.status_code == 422
    path = tmp_path / 'pds_quickbooks_numbering.json'
    path.write_text('{ broken')
    with pytest.raises(HTTPException) as ex:
        route.numbering(request)
    assert ex.value.status_code == 503


def test_future_provider_verified_invoice_reference_one_to_one(tmp_path):
    request, doc = setup_request(tmp_path)
    args = dict(kind='invoice', doorks_number='JS00021', company_id='PDS_COMPANY',
                quickbooks_id='QBO-543', quickbooks_number='17566')
    with pytest.raises(HTTPException) as ex:
        numbering.verified_reference(request, **args)
    assert ex.value.status_code == 422
    result = numbering.verified_reference(request, **args, checked_against_provider=True)
    assert result['record']['doorks_number'] == 'JS00021'
    assert result['record']['quickbooks_number'] == '17566'
    assert result['duplicate'] is False
    assert numbering.verified_reference(request, **args, checked_against_provider=True)['duplicate'] is True
    assert doc['number'] == 'JS00021'  # never rewrites saved PDS invoice
    with pytest.raises(HTTPException) as ex:
        numbering.verified_reference(request, **{**args, 'quickbooks_number': '17567'}, checked_against_provider=True)
    assert ex.value.status_code == 409
    assert route.numbering(request)['verified_reference_count'] == 1


def test_reject_two_doorks_documents_for_one_qb_object(tmp_path):
    request, doc = setup_request(tmp_path)
    more = dict(doc)
    more['number'] = 'JS00022'
    request.app.state.documents_store.list_documents=lambda: [doc, more]
    first = dict(kind='invoice', doorks_number='JS00021', company_id='company-1',
                 quickbooks_id='qb-3', quickbooks_number='17566', checked_against_provider=True)
    numbering.verified_reference(request, **first)
    with pytest.raises(HTTPException) as ex:
        numbering.verified_reference(request, **{**first, 'doorks_number':'JS00022'})
    assert ex.value.status_code == 409
    with pytest.raises(HTTPException) as ex:
        numbering.verified_reference(request, **{**first, 'doorks_number':'JS00022', 'quickbooks_id':'qb-4'})
    assert ex.value.status_code == 409
    with pytest.raises(HTTPException) as ex:
        numbering.verified_reference(request, **{**first, 'doorks_number':'JS00099', 'quickbooks_id':'qb-4'})
    assert ex.value.status_code == 409


def test_supplier_po_reference_preserves_pds_and_customer_numbers(tmp_path):
    request, row, path = po_fixture(tmp_path)
    result = numbering.verified_reference(request, kind='supplier_po',
        doorks_number='PO-00020', company_id='company-A', quickbooks_id='qb-po-200',
        quickbooks_number='17567', checked_against_provider=True)
    assert result['record']['quickbooks_number'] == '17567'
    assert json.loads(path.read_text())[0]['po_number'] == 'PO-00020'
    assert json.loads(path.read_text())[0]['work_order'] == '1126-20'


def test_ui_contains_numbering_tab_and_does_not_enable_sync():
    js = (ROOT / 'static/app.js').read_text()
    css = (ROOT / 'static/pds_quickbooks_hub.css').read_text()
    for expected in ('data-qbh-tab="numbering"', 'qbhSaveNumbering',
                     '/pds-quickbooks/numbering', 'No documents will be renumbered.',
                     'QuickBooks number', 'numberingLabels'):
        assert expected in js
    assert '.qbh-number-row' in css and '.qbh-number-steps' in css
    assert "'automatic_sync_enabled': False" in (ROOT/'app/services/pds_quickbooks_numbering.py').read_text()
