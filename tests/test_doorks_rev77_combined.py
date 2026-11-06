"""Static regression checks for Rev77 portal routes and UX wiring."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_customer_intake_scoped_and_office_review():
    source=(ROOT/'app/routers/doorks_portals.py').read_text()
    section=source.split("@router.post('/accounts/work-orders/new-request')",1)[1].split('class CustomerWorkOrderChange',1)[0]
    assert '_portal_user(request)' in section
    assert "'status':'pending_review'" in section
    assert "'delivery':'office_only'" in section
    assert "payload.vendor_id" not in section

def test_vendor_generator_is_separate_and_uses_existing_endpoint():
    html=(ROOT/'static/doorks_home.html').read_text()
    assert 'function portalVendorGenerator(assignment,type)' in html
    assert "vendor-account/commercial-documents" in html
    assert 'Create Estimate' in html and 'Create Invoice' in html

def test_moses_seclock_rixson_brand_hint():
    source=(ROOT/'app/routers/moses.py').read_text()
    assert 'Rixson|Adams Rite' in source
