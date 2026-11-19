"""Release qualification for the PDS 5.45 cumulative UI/business repair."""
from pathlib import Path
from types import SimpleNamespace
import asyncio
import pytest
from fastapi import HTTPException
from app.routers import pds_scheduling, pds_purchase_orders, door_logs
from app.routers.document_vault import validate_type

ROOT = Path(__file__).resolve().parents[1]


def test_schedule_excludes_inactive_employee_even_when_login_remains_active():
    employees = [
        {'id':'1','name':'Current Tech','role':'tech','status':'Active','active':True},
        {'id':'2','name':'Former Tech','role':'tech','status':'Inactive','active':True,'email':'former@pds.example'},
    ]
    users = [
        {'id':'login1','name':'Current Tech','role':'tech','active':True},
        {'id':'login2','name':'Former Tech','role':'tech','email':'former@pds.example','active':True},
        {'id':'login3','name':'Office Only','role':'office','active':True},
    ]
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        employees_store=SimpleNamespace(list=lambda:employees),
        users_store=SimpleNamespace(list_users=lambda:users))))
    staff = pds_scheduling._people(request)
    names = {row['name'] for row in staff}
    assert 'Current Tech' in names
    assert 'Former Tech' not in names
    assert 'Office Only' in names


def test_unreceived_po_delete_requires_admin_and_preserves_data(tmp_path):
    root=tmp_path/'pds_purchase_orders';root.mkdir()
    (root/'records.json').write_text('[{"id":"p1","po_number":"PO-00001"}]')
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
                           state=SimpleNamespace(auth_user={'id':'1'},auth_role='office'),
                           session={'active_platform':'pds'})
    with pytest.raises(HTTPException) as exc:
        pds_purchase_orders.delete_purchase_order('pds','p1',request)
    assert exc.value.status_code==403
    assert 'PO-00001' in (root/'records.json').read_text()
    request.state.auth_role='office_admin'
    pds_purchase_orders.delete_purchase_order('pds','p1',request)
    assert 'PO-00001' not in (root/'records.json').read_text()


def test_receiving_status_filters_completed_and_rejected_purchases(tmp_path):
    folder=tmp_path/'pds_purchase_orders';folder.mkdir()
    (folder/'records.json').write_text('[\n      {"id":"a","po_number":"PO-00001","vendor":"Supplier","quantity":2,"status":"New"},\n      {"id":"b","po_number":"PO-00002","vendor":"Supplier","quantity":1,"status":"Rejected"}\n    ]')
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path)),
                           state=SimpleNamespace(auth_user={'id':'1'},auth_role='office_admin'),
                           session={'active_platform':'pds'})
    orders=pds_purchase_orders.list_receiving('pds',request)['orders']
    assert [o['receiving_status'] for o in orders]==['Pending','Rejected']


def test_door_ai_is_authenticated_and_never_saves_without_manual_step():
    request=SimpleNamespace(state=SimpleNamespace(auth_user=None,auth_role='tech'),session={'active_platform':'pds'})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(door_logs.preview_door_record(request,notes_text='Stanley door',file=None))
    assert exc.value.status_code==401
    source=Path(door_logs.__file__).read_text()
    assert 'draft_only' in source and 'requires_review' in source
    assert '.create(' not in source.split('async def preview_door_record(')[1].split('@router.get("/door-logs")')[0]


def test_document_types_are_reference_uploads_not_numbered_documents():
    for kind in ('estimate','invoice','purchase_order','part_reference','supplier_document','customer_document'):
        assert validate_type(kind)==kind


def test_ui_has_all_cumulative_requested_workflows():
    js=(ROOT/'static/app.js').read_text()
    markup=(ROOT/'templates/ui.html').read_text()
    for expected in ('🚚 Receiving','📦 Inventory', 'receiveFilter','Delete Unreceived PO',
                     'renderPdsBusinessSettingsHub','renderPdsAccountingSettingsHub',
                     'const currentFleetTotal=', 'Next Service - ',
                     "head.style.display='none'", 'Save Door Record', 'pds-ticket-action-panel',
                     'door-logs/ai-preview','🎙 Dictate', 'Apply Reviewed Fields',
                     'Last Upload', "job_number"):
        assert expected in js, expected
    assert 'Field Flow' in markup
    assert 'Office Flow' in markup and 'Job Flow' in markup
    assert 'Packing Slips / AI Upload' not in js
    assert 'const refreshReceipts = async()=>{};' in js  # Field Flow cannot retrieve shared receipt history
