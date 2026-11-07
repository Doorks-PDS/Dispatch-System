from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_office_reference_fields_use_shared_factory():
    app = (ROOT / 'static/app.js').read_text()
    shared = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert "[row4, 'ej_inv', 'invoice_number']" in app
    assert "[rowQuote, 'ej_quote_assigned', 'quote_assigned_to']" in app
    assert "[rowQuote, 'ej_sent_quote', 'sent_quote_number']" in app
    assert 'sharedTicketEditor.createTicketFieldInput(field' in app
    for field in ('invoice_number', 'quote_assigned_to', 'sent_quote_number'):
        assert field in shared

def test_document_editor_still_uses_shared_line_rows():
    app = (ROOT / 'static/app.js').read_text()
    assert 'DoorksSharedTicket?.createDocumentLineRow' in app
    assert 'DoorksSharedTicket?.calculateDocumentTotals' in app
