from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_ticket_renderer_is_real_reusable_component():
    source = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert 'root.DoorksSharedTicket={render,renderTicketFields' in source
    assert 'createLineEditor,createDocumentWorkspace,validateDocumentDraft,createDocumentLineRow,calculateDocumentTotals' in source
    assert 'textContent=String(value)' in source  # untrusted values are not interpolated into HTML
    assert 'vendor_assignments' in source


def test_customer_and_vendor_use_live_work_order_ticket():
    portal = (ROOT / 'static/doorks_home.html').read_text()
    assert "api('tickets/'+encodeURIComponent(workOrderId))" in portal
    assert 'DoorksSharedTicket.openTicket({host:section,record:response.ticket' in portal
    assert '/static/doorks_shared_ticket.js' in portal
    assert 'DoorksSharedTicket.renderDocument(preview,' in portal
    assert 'DoorksSharedTicket.renderDocument(preview,editor.draft()' in portal


def test_office_vendor_review_uses_same_document_component_and_existing_builder():
    office = (ROOT / 'static/app.js').read_text()
    assert 'async function doorksLoadSharedTicket()' in office
    assert 'DoorksSharedTicket.renderDocument(sharedDoc,doc,{vendor:true})' in office
    assert 'window.__doorksOpenCustomerDocumentDraft' in office


def test_no_new_data_store_or_portal_accounting_posting():
    source = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert 'fetch(' not in source
    assert 'localStorage' not in source


def test_vendor_line_editor_is_shared_and_not_a_second_portal_implementation():
    portal = (ROOT / 'static/doorks_home.html').read_text()
    shared = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert "DoorksSharedTicket.openDocument({role:'vendor',host:rows,items,documentType:type" in portal
    assert 'function createLineEditor(host,options={})' in shared
    assert 'const redraw=()=>{rows.replaceChildren();items.forEach' not in portal
    assert 'fetch(' not in shared
