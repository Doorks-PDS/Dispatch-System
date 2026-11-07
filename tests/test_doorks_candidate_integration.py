"""Release-candidate interface and server authorization contracts.
These tests do not substitute for staging browser testing.
"""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text()
PORTAL=(ROOT/'static/doorks_home.html').read_text()
SHARED=(ROOT/'static/doorks_shared_ticket.js').read_text()
API=(ROOT/'app/routers/doorks_portals.py').read_text()

def test_office_ticket_uses_shared_renderer_and_editor_factory():
    assert 'shared.renderTicketFields(fields, job' in APP
    assert 'sharedTicketEditor.createTicketFieldInput(field' in APP
    assert 'apiUpdateJob(job.id' in APP

def test_office_document_uses_real_original_builder_and_shared_line_math():
    assert 'async function openEstimateInvoiceDrawer(' in APP
    assert 'shared.registerOfficeControllers({' in APP
    assert 'document:({job=null,type=' in APP
    assert 'window.DoorksSharedTicket?.createDocumentLineRow' in APP
    assert 'window.DoorksSharedTicket?.calculateDocumentTotals' in APP
    assert 'doc_generate' in APP

def test_portals_use_role_aware_ticket_and_document_entrypoints():
    assert "DoorksSharedTicket.openTicket({host:section,record:response.ticket||{},role:response.role" in PORTAL
    assert "DoorksSharedTicket.openDocument({role:'vendor'" in PORTAL
    assert 'DoorksSharedTicket.renderDocument(preview' in PORTAL
    assert "if(policy.office){" in SHARED
    assert "if(policy.proposeDocument){" in SHARED
    assert "throw Error('Document editing is not permitted for this role')" in SHARED

def test_customer_and_vendor_requests_require_authenticated_ownership():
    assert "@router.post('/accounts/work-orders/change-request')" in API
    assert "@router.post('/vendor-account/assignments/change-request')" in API
    assert "@router.post('/admin/operational-change-requests/{submission_id}/decision')" in API
    assert "@router.post('/admin/operational-change-requests/{submission_id}/mark-applied')" in API
    assert "raise HTTPException(409, 'Use the operational change decision workflow')" in API

def test_no_automatic_source_write_in_operational_decision():
    body=API.split('def decide_operational_change(',1)[1].split('class OperationalChangeApplied',1)[0]
    assert 'workspace_items(' not in body
    assert "applied_to_source=False" in body
    assert "'approved_pending_application'" in body

def test_shared_module_does_not_issue_documents_for_portals():
    body=SHARED.split('function openDocument(',1)[1].split('function officeControllerStatus(',1)[0]
    assert 'nativeOffice.document(context)' in body
    assert 'createLineEditor(context.host' in body
    assert 'issueDocument' not in body
