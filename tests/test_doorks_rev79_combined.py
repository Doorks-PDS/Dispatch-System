"""Rev79 security/route smoke checks (not a substitute for browser or integration tests)."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_customer_estimate_route_scopes_to_session_and_queues_review():
    source=(ROOT/'app/routers/doorks_portals.py').read_text()
    segment=source.split("@router.post('/accounts/estimates/respond')",1)[1].split("@router.post('/vendor-account/moses-document')",1)[0]
    assert '_portal_user(request)' in segment
    assert "'record_id': account['customer_id']" in segment
    assert "'document_type'] == 'Estimate'" in segment
    assert "'status': 'pending_review'" in segment
    assert 'write(path, obj)' in segment
    assert 'invoice_record(' not in segment

def test_vendor_moses_requires_owned_assignment():
    source=(ROOT/'app/routers/doorks_portals.py').read_text()
    segment=source.split("@router.post('/vendor-account/moses-document')",1)[1].split("@router.get('/accounts/payments')",1)[0]
    assert '_vendor_user(request)' in segment
    assert '_vendor_assignment_owned(request, account, assignment_id)' in segment
    assert 'finally:' in segment
    assert 'portal_moses_authorized = False' in segment

def test_customer_preview_and_moses_draft_ui():
    html=(ROOT/'static/doorks_home.html').read_text()
    assert "accounts/estimates/respond" in html
    assert "doc.line_items||[]" in html
    assert "vendor-account/moses-document" in html
    assert 'Moses draft populated' in html
