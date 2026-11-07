from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_office_ticket_uses_shared_edit_input_factory():
    office = (ROOT / 'static/app.js').read_text()
    shared = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert 'sharedTicketEditor.createTicketFieldInput(field' in office
    assert "createTicketFieldInput('requested_date'" in shared
    assert "createTicketFieldInput('requested_time'" in shared

def test_portal_cannot_edit_office_fields():
    shared = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert "Portal cannot edit office ticket fields" in shared
    assert "['requested_date','requested_time'].includes(kind)" in shared
