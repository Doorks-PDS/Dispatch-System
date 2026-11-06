from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_vendor_field_updates_are_scoped_and_restricted():
    source=(ROOT/'app/routers/doorks_portals.py').read_text()
    segment=source.split("@router.post('/vendor-account/assignments/field-update')",1)[1].split('# Rev 73:',1)[0]
    assert "_vendor_user(request)" in segment
    assert "str(x.get('vendor_id'))==str(account['vendor_id'])" in segment
    assert "draft','declined','cancelled','completed','finished" in segment
    assert 'row[\'vendor_field_history\']' in segment
    assert 'ws.save(path,rows)' in segment

def test_compliance_upload_vendor_ownership_and_file_validation():
    source=(ROOT/'app/routers/doorks_portals.py').read_text()
    segment=source.split("@router.post('/vendor-account/upload')",1)[1].split("@router.post('/accounts/register')",1)[0]
    assert "str(record_id)==str(account['vendor_id'])" in segment
    assert "5*1024*1024" in segment
    assert "Only PDF, JPG, PNG or WEBP supported" in segment

def test_office_active_queue_and_vendor_ui():
    office=(ROOT/'static/app.js').read_text()
    portal=(ROOT/'static/doorks_home.html').read_text()
    assert office.index('Assignment queue</h3>')<office.index('Vendor directory & onboarding</h3>')
    assert "'completed','finished','cancelled','declined'" in office
    assert 'Insurance & Licensing' in portal
    assert 'assignments/field-update' in portal
