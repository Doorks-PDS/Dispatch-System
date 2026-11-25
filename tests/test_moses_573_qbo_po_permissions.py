"""5.73: staff-visible POs; Office-only PO mutations and delivery; source form shortcut."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.routers import pds_purchase_orders as pds_po
from app.routers import workspaces as ws
from app.services import moses_po_delivery


def req(tmp_path, role, platform='pds'):
    state = SimpleNamespace(data_dir=tmp_path)
    return SimpleNamespace(
        state=SimpleNamespace(auth_role=role, auth_user={'id': 'test-id', 'name': 'Test User', 'username': 'test'}),
        session={'active_platform': platform},
        app=SimpleNamespace(state=state),
    )


def assert_denied(call):
    with pytest.raises(HTTPException) as error:
        call()
    assert error.value.status_code == 403


def test_pds_staff_can_view_po_but_not_create_or_edit(tmp_path):
    office = req(tmp_path, 'office')
    record = pds_po.create_order(pds_po.POInput(data={
        'vendor':'Supplier', 'description':'Fasteners', 'quantity':'2', 'unit_cost':'12',
        'total':'24', 'status':'Draft'
    }), office)
    assert record['po_number'] == 'PO-00001'
    for role in ('lead', 'tech'):
        read_request = req(tmp_path, role)
        assert pds_po.list_orders(read_request)['items'][0]['id'] == record['id']
        assert_denied(lambda:pds_po.create_order(pds_po.POInput(data={'vendor':'Supplier'}),read_request))
        assert_denied(lambda:pds_po.update_order(record['id'],pds_po.POInput(data={'status':'Ordered'}),read_request))
        assert_denied(lambda:moses_po_delivery._guard(read_request, 'pds', require_send_enabled=False))
    assert record['status']=='Draft'
    updated=pds_po.update_order(record['id'],pds_po.POInput(data={'status':'Ordered'}),office)
    assert updated['status']=='Ordered'
    moses_po_delivery._guard(office, 'pds', require_send_enabled=False)
    moses_po_delivery._guard(req(tmp_path, 'office_admin'), 'pds', require_send_enabled=False)
    assert len(pds_po.list_orders(office)['items'])==1


def test_workspace_purchase_orders_are_read_only_for_leads_and_techs(tmp_path):
    for platform in ('doorks','sdc'):
        office=req(tmp_path,'office',platform)
        saved=ws.create(platform,'purchase_orders',ws.Record(data={'vendor':'Supplier','status':'Draft'}),office)['item']
        for role in ('lead','tech'):
            r=req(tmp_path,role,platform)
            assert ws.listing(platform,'purchase_orders',r)['items'][0]['id']==saved['id']
            assert_denied(lambda:ws.create(platform,'purchase_orders',ws.Record(data={'vendor':'Other'}),r))
            assert_denied(lambda:ws.update(platform,'purchase_orders',saved['id'],ws.Record(data={'status':'Ordered'}),r))
            assert_denied(lambda:ws.delete(platform,'purchase_orders',saved['id'],r))
            assert_denied(lambda:moses_po_delivery._guard(r,platform,require_send_enabled=False))
        updated=ws.update(platform,'purchase_orders',saved['id'],ws.Record(data={'status':'Ordered'}),office)['item']
        assert updated['status']=='Ordered'
        moses_po_delivery._guard(office,platform,require_send_enabled=False)
        admin=req(tmp_path,'office_admin',platform)
        assert ws.listing(platform,'purchase_orders',admin)['items'][0]['id']==saved['id']


def test_purchase_order_ui_has_view_only_staff_controls_and_pds_form_handoff():
    js=(Path(__file__).parents[1]/'static/app.js').read_text()
    assert "const canManagePO=['office','office_admin'].includes" in js
    assert "q('upoNew').hidden=!canManagePO" in js
    assert "poEmailButton.hidden=!canManagePO" in js
    assert "...(canManagePO?[['Edit',()=>edit(item)]]:[])" in js
    assert '✦ Save & Estimate' in js
    assert "String(form?.id || '') === String(savedForm?.id || '')" in js
    assert 'helperPrefill:{autoFill:true,sourceIndex,tripQty:1,fuelQty:1}' in js
    assert 'Ready to Quote' in js
