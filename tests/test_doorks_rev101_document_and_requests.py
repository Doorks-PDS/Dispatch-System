from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_shared_document_validation_used_by_office_and_vendor():
    shared=(ROOT/'static/doorks_shared_ticket.js').read_text()
    office=(ROOT/'static/app.js').read_text()
    assert 'function validateDocumentLines(' in shared
    assert 'const validate=()=>validateDocumentLines(items)' in shared
    assert 'DoorksSharedTicket?.validateDocumentLines?.(items)' in office
    assert 'if (!lineCheck.valid)' in office

def test_request_validation_is_role_specific_and_server_checked():
    shared=(ROOT/'static/doorks_shared_ticket.js').read_text()
    server=(ROOT/'app/routers/doorks_portals.py').read_text()
    assert '(vendor?5:3)' in shared
    section=server.split("@router.post('/accounts/work-orders/change-request')",1)[1].split('@router.',1)[0]
    assert "datetime.strptime(payload.requested_date, '%Y-%m-%d')" in section
    assert "datetime.strptime(payload.requested_time, '%H:%M')" in section
    assert "'status':'pending_review'" in section
