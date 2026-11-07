from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = (ROOT / 'static/doorks_shared_ticket.js').read_text()
OFFICE = (ROOT / 'static/app.js').read_text()


def test_one_shared_ticket_field_renderer():
    assert 'function renderTicketFields(host,record,options={})' in SHARED
    assert 'renderTicketFields(grid,r,{role,only:labels})' in SHARED
    assert 'shared.renderTicketFields(fields, job' in OFFICE


def test_office_metadata_not_exposed_to_portals():
    assert 'if(field.office&&!office)continue' in SHARED
    for label in ['Invoice #', 'Estimate #', 'Quote Assigned To']:
        assert f"label:'{label}'" in SHARED


def test_text_content_not_html_injection():
    assert 'e.textContent=String(value)' in SHARED
    assert 'host.replaceChildren()' in SHARED
