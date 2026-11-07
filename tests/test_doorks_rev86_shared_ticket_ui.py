from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'static/doorks_home.html').read_text()

def test_shared_ticket_is_role_scoped():
    assert "api('tickets/'+encodeURIComponent(workOrderId))" in HTML
    assert "response.role==='vendor'" in HTML
    assert "response.role==='customer'" in HTML

def test_vendor_proposal_has_itemized_ticket():
    assert "Office review required before customer issuance" in HTML
    assert "DoorksSharedTicket.renderDocument" in HTML
