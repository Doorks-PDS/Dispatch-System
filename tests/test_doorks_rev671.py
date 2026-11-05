import json
from pathlib import Path
from types import SimpleNamespace
from app.routers import doorks_portals as portal

class Request:
    def __init__(self,root):
        self.app=SimpleNamespace(state=SimpleNamespace(data_dir=root))
        self.state=SimpleNamespace(auth_user='admin',auth_role='office_admin')
        self.session={'active_platform':'doorks'}

def test_invitation_submission_idempotency(tmp_path,monkeypatch):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    p=root/'portal_access.json';p.write_text(json.dumps({'invites':[],'submissions':[]}))
    monkeypatch.setattr(portal,'access',lambda req,token:{'id':'invite1','kind':'customer','company':'Example','record_id':'customer1','contact_name':'Test','contact_email':'test@example.com'})
    req=Request(tmp_path)
    payload=portal.Submission(token='token',subject='Repair',message='Door broken',request_id='submission-123')
    first=portal.submit(payload,req);second=portal.submit(payload,req)
    assert first['submission_id']==second['submission_id']
    assert second['duplicate'] is True
    assert len(json.loads(p.read_text())['submissions'])==1

def test_new_work_order_uses_requested_date_but_not_confirmed(tmp_path):
    root=tmp_path/'business_workspaces'/'doorks';root.mkdir(parents=True)
    (root/'vendors.json').write_text(json.dumps([{'id':'v1','name':'Vendor'}]))
    (root/'portal_access.json').write_text(json.dumps({'invites':[],'submissions':[{'id':'i1','kind':'public_service_request','company':'Example','preferred_date':'2026-11-16','message':'Door repair'}]}))
    portal.link_inquiry_vendor(portal.VendorInquiryLink(submission_id='i1',vendor_id='v1'),Request(tmp_path))
    job=json.loads((root/'work_orders.json').read_text())[0]
    assert job['scheduled_date']=='2026-11-16'
    assert job['date']=='2026-11-16'
    assert 'pending' in job['schedule_confirmation'].lower()
