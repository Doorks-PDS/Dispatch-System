from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_customer_uses_shared_document_component():
    portal=(ROOT/'static/doorks_home.html').read_text()
    section=portal.split('function portalDocumentDetails(doc){',1)[1].split('function portalHeading(',1)[0]
    assert 'DoorksSharedTicket.renderDocument(preview' in section
    assert "const table=document.createElement('table')" not in section
    assert 'doc.has_original' in section
    assert "accounts/estimates/respond" in section

def test_shared_document_accepts_both_office_and_vendor_quantity_fields():
    shared=(ROOT/'static/doorks_shared_ticket.js').read_text()
    assert 'line.qty??line.quantity' in shared
    assert 'd.amount' in shared
    assert 'calculateDocumentTotals(lines' in shared
    assert 'textContent=String(value)' in shared
