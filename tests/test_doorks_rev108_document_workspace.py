from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHARED=(ROOT/'static/doorks_shared_ticket.js').read_text()
OFFICE=(ROOT/'static/app.js').read_text()
PORTAL=(ROOT/'static/doorks_home.html').read_text()

def test_vendor_document_workspace_uses_shared_rows_and_preview():
    assert 'function createDocumentWorkspace(host,options={})' in SHARED
    assert 'createLineEditor(lineHost' in SHARED
    assert 'renderDocument(preview,draft(),{vendor:true})' in SHARED
    assert 'return createDocumentWorkspace(context.host' in SHARED
    assert 'reference:reference.value.trim()' in SHARED

def test_office_document_issuance_keeps_native_controller_and_preflight():
    assert 'return nativeOffice.document(context)' in SHARED
    assert 'function validateDocumentDraft(context={})' in SHARED
    assert "validateDocumentDraft?.({role:'office'" in OFFICE
    assert 'apiCreateInvoice(payload)' in OFFICE
    assert 'apiCreateEstimate(payload)' in OFFICE

def test_vendor_reference_comes_from_shared_editor():
    assert 'const ref=editor.reference;' in PORTAL
    assert 'documentType:type,workOrderNumber:assignment.work_order_number' in PORTAL
    assert 'buildVendorDocumentSubmission' in PORTAL
