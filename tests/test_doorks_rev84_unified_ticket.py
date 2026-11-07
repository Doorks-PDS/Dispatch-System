"""Rev84 focused regression tests for role-scoped shared tickets and queue safety."""
from types import SimpleNamespace
from pathlib import Path
from fastapi import HTTPException
from app.routers import doorks_portals as portal


def _request(role=None, platform=None, account='a'):
    return SimpleNamespace(state=SimpleNamespace(auth_role=role, auth_user='tester'),
                           session={'active_platform':platform, 'doorks_portal_account':account})


def test_ticket_customer_is_scoped(monkeypatch):
    job={'id':'job-1','customer_id':'customer-1','customer':'Example','status':'Scheduled','notes':'PRIVATE'}
    monkeypatch.setattr(portal,'workspace_items',lambda request,kind:[job] if kind=='work_orders' else [])
    monkeypatch.setattr(portal,'read',lambda path:{'accounts':[{'id':'a','status':'active','role':'customer'}]})
    monkeypatch.setattr(portal,'store',lambda request:None)
    monkeypatch.setattr(portal,'_portal_user',lambda request:{'customer_id':'customer-1'})
    result=portal.shared_work_order_ticket('job-1',_request())
    assert result['role']=='customer'
    assert result['ticket']['status']=='Scheduled'
    assert 'notes' not in result['ticket']
    assert not result['permissions']['view_vendor_costs']
    monkeypatch.setattr(portal,'_portal_user',lambda request:{'customer_id':'another'})
    try:portal.shared_work_order_ticket('job-1',_request())
    except HTTPException as e:assert e.status_code==404
    else:assert False,'Customer could access another customer work order'


def test_ticket_vendor_requires_assignment(monkeypatch):
    job={'id':'job-1','customer_id':'customer-1'}
    assignment={'id':'assignment-1','work_order_id':'job-1','vendor_id':'vendor-1','status':'accepted','vendor_field_notes':'Working'}
    monkeypatch.setattr(portal,'workspace_items',lambda request,kind:[job] if kind=='work_orders' else [assignment])
    monkeypatch.setattr(portal,'read',lambda path:{'accounts':[{'id':'a','status':'active','role':'vendor'}]})
    monkeypatch.setattr(portal,'store',lambda request:None)
    monkeypatch.setattr(portal,'_vendor_user',lambda request:{'vendor_id':'vendor-1'})
    result=portal.shared_work_order_ticket('job-1',_request())
    assert result['ticket']['vendor_assignments'][0]['vendor_field_notes']=='Working'
    assert not result['permissions']['edit_dispatch']
    monkeypatch.setattr(portal,'_vendor_user',lambda request:{'vendor_id':'other-vendor'})
    try:portal.shared_work_order_ticket('job-1',_request())
    except HTTPException as e:assert e.status_code==404
    else:assert False,'Vendor could access another vendor work order'


def test_ticket_office_view(monkeypatch):
    job={'id':'job-1','notes':'office private'}
    monkeypatch.setattr(portal,'workspace_items',lambda request,kind:[job] if kind=='work_orders' else [])
    result=portal.shared_work_order_ticket('job-1',_request('office_admin','doorks'))
    assert result['ticket']['notes']=='office private'
    assert result['permissions']['edit_dispatch']


def test_queue_action_preserves_records(monkeypatch):
    saved=[]
    data={'submissions':[{'id':'inq','status':'pending_review','work_order_id':'job-1'}],
          'review_history':[],'vendor_commercial_documents':[{'id':'financial'}]}
    monkeypatch.setattr(portal,'admin',lambda request:None)
    monkeypatch.setattr(portal,'store',lambda request:None)
    monkeypatch.setattr(portal,'read',lambda path:data)
    monkeypatch.setattr(portal,'write',lambda path,obj:saved.append(obj.copy()))
    result=portal.submission_queue_action('inq',portal.SubmissionQueueAction(action='delete'),_request())
    assert result['ok']
    assert data['submissions'][0]['deleted_at']
    assert data['submissions'][0]['work_order_id']=='job-1'
    assert data['vendor_commercial_documents'][0]['id']=='financial'


def test_office_document_edits_audited(monkeypatch):
    data={'vendor_commercial_documents':[{'id':'doc-1','status':'submitted_for_review','amount':5,'line_items':[]}]}
    monkeypatch.setattr(portal,'admin',lambda request:None)
    monkeypatch.setattr(portal,'store',lambda request:None)
    monkeypatch.setattr(portal,'read',lambda path:data)
    monkeypatch.setattr(portal,'write',lambda path,obj:None)
    payload=portal.VendorDocumentOfficeEdit(line_items=[portal.VendorLineItem(description='Repair',quantity=2,rate=175)])
    result=portal.office_edit_vendor_document('doc-1',payload,_request())
    assert result['document']['amount']==350
    assert result['document']['revision_history'][0]['before']['amount']==5
