from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_office_ticket_mounts_shared_editor_with_existing_save_api():
    source = (ROOT / 'static/app.js').read_text()
    assert 'Quick Edit Ticket Details' in source
    assert 'shared.createTicketEditPanel(editBody' in source
    assert "role: 'office', fields: fieldsToEdit, values: job" in source
    assert 'await apiUpdateJob(job.id, {...values})' in source
    assert 'renderJobDetails(container, updated, ctx)' in source

def test_portal_and_office_share_ticket_editor_factory():
    source = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert 'function createTicketEditPanel(host,options={})' in source
    assert 'const input=createTicketFieldInput(field,' in source
    assert "const date=createTicketFieldInput('requested_date'" in source
    assert "const time=createTicketFieldInput('requested_time'" in source
