from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_vendor_submission_uses_shared_payload():
    shared = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    portal = (ROOT / 'static/doorks_home.html').read_text()
    assert 'function buildVendorDocumentSubmission(context={})' in shared
    assert 'buildVendorDocumentSubmission({assignmentId:assignment.id' in portal
    assert 'JSON.stringify(payload)' in portal
    assert "if(!['estimate','invoice'].includes(type))" in shared
    assert 'validateDocumentLines(lines)' in shared
    assert 'calculateDocumentTotals(normalized).subtotal' in shared
