from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_change_request_is_vendor_scoped_and_not_direct_dispatch_edit():
    src=(ROOT/'app/routers/doorks_portals.py').read_text()
    block=src.split("@router.post('/vendor-account/assignments/change-request')",1)[1].split("@router.get('/vendor-account/compliance')",1)[0]
    assert '_vendor_user(request)' in block
    assert '_vendor_assignment_owned(request, account, payload.assignment_id)' in block
    assert "'status':'pending_review'" in block
    assert "obj['submissions'].append(entry)" in block
    assert 'ws.save' not in block

def test_compliance_list_only_current_vendor_and_review_requires_admin():
    src=(ROOT/'app/routers/doorks_portals.py').read_text()
    block=src.split("@router.get('/vendor-account/compliance')",1)[1].split('class VendorComplianceReview',1)[0]
    assert '_vendor_user(request)' in block
    assert "str(x.get('record_id'))==str(account['vendor_id'])" in block
    review=src.split("@router.post('/admin/vendor-compliance/",1)[1]
    assert 'admin(request)' in review
    assert "entry.get('status')!='pending_review'" in review

def test_portal_ui_exposes_real_routes():
    html=(ROOT/'static/doorks_home.html').read_text()
    assert 'vendor-account/assignments/change-request' in html
    assert 'vendor-account/compliance' in html
    assert "fd.append('expires_on',expires.value)" in html
    assert 'This document has no itemized lines available' in html
