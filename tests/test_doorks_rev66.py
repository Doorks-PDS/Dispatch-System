import json
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException
from app.routers import doorks_portals as portal

class FakeRequest:
    def __init__(self, root):
        self.app=SimpleNamespace(state=SimpleNamespace(data_dir=root))
        self.state=SimpleNamespace(auth_user='admin',auth_role='office_admin')
        self.session={'active_platform':'doorks'}

def test_vendor_inquiry_creates_one_work_order_and_one_draft_assignment(tmp_path):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    (root/'vendors.json').write_text(json.dumps([{'id':'vendor1','name':'Example Vendor','onboarding_status':'Approved'}]))
    (root/'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[{'id':'inq1','kind':'public_service_request','company':'New Customer','contact_name':'Client','address':'Test Street','message':'Repair door','status':'pending_review'}],'notifications':[],'payment_links':[]}))
    req=FakeRequest(tmp_path)
    data=portal.VendorInquiryLink(submission_id='inq1',vendor_id='vendor1')
    first=portal.link_inquiry_vendor(data,req)
    assert first['work_order_number']
    assert first['work_order_id']
    jobs=json.loads((root/'work_orders.json').read_text())
    assignments=json.loads((root/'vendor_assignments.json').read_text())
    assert len(jobs)==len(assignments)==1
    assert assignments[0]['status']=='Draft'
    assert assignments[0]['work_order_id']==jobs[0]['id']
    second=portal.link_inquiry_vendor(data,req)
    assert second['work_order_id']==first['work_order_id']
    assert len(json.loads((root/'work_orders.json').read_text()))==1
    assert len(json.loads((root/'vendor_assignments.json').read_text()))==1

def test_mismatched_existing_customer_link_is_blocked(tmp_path):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    (root/'vendors.json').write_text(json.dumps([{'id':'vendor1','name':'Vendor'}]))
    (root/'work_orders.json').write_text(json.dumps([{'id':'job1','customer_id':'other-customer'}]))
    (root/'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[{'id':'inq1','kind':'customer','record_id':'customer1'}]}))
    try:portal.link_inquiry_vendor(portal.VendorInquiryLink(submission_id='inq1',vendor_id='vendor1',work_order_id='job1'),FakeRequest(tmp_path))
    except HTTPException as exc:assert exc.status_code==409
    else:assert False,'Mismatch should be rejected'
