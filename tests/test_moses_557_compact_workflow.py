"""Source regressions for cumulative Moses 5.57 UI, save feedback and RFQ workflow."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'static/app.js').read_text()
CSS=(ROOT/'static/style.css').read_text()
RFQ=(ROOT/'app/routers/pds_supplier_quotes.py').read_text()

def section(start, end):
    a=JS.index(start)
    return JS[a:JS.index(end,a)]


def test_bounded_photo_viewer_is_not_a_scrolling_strip():
    viewer=section('function pdsCompactPhotoViewer(', 'function pdsFormPhotoCarousel(')
    assert 'grid-template-columns:repeat(3,minmax(0,1fr))' in viewer
    assert 'Math.floor(index/3)*3' in viewer
    assert 'Math.min(start+3,files.length)' in viewer
    assert "previous.onclick=()=>" in viewer and "next.onclick=()=>" in viewer
    assert 'openAttachmentCarousel(files,index)' in viewer
    assert 'overflow-x:auto' not in viewer
    gallery=section('function pdsFormPhotoCarousel(', 'function openEstimateInvoiceHelper(')
    assert 'buildCompletionAttachmentUrl' in gallery
    assert 'buildJobAttachmentUrl' in gallery
    assert 'pdsCompactPhotoViewer(files' in gallery


def test_both_generators_have_one_new_button_next_to_search():
    helper=section('function openEstimateInvoiceHelper(', 'function openEstimateDrawer(')
    editor=section('function openEstimateInvoiceDrawer(', 'function pdsCompletedInvoiceText(') if 'function openEstimateInvoiceDrawer(' in JS else JS
    assert 'id="helper_part_search"' in helper and 'id="helper_new_part"' in helper
    assert '＋ New' in helper
    assert 'id="part_lookup"' in editor and 'id="part_lookup_new"' in editor
    assert "card.querySelector('#part_lookup_new').onclick" in editor
    assert 'Add New Part or Service  ·  Moses intake' not in editor
    catalog=section('function pdsQuickCatalogEditor(', 'function pdsQuickSupplierQuoteRequest(')
    assert "['part','📦 Part / Product']" in catalog
    assert "['service','🛠️ Service / Subcontractor']" in catalog
    assert "opt.value='supplier_quote'" in catalog
    assert 'api.dismiss({__supplierQuoteRequest:true' in catalog
    assert 'if(saved.__supplierQuoteRequest)' in editor


def test_compact_supplier_quote_email_preserves_server_send_controls():
    queue=section('async function openPdsJobFlowWorkQueue()', 'function renderJobFlowView(')
    form=section('function pdsQuickSupplierQuoteRequest(', '// Send saved PDS estimates/invoices')
    assert "formField(form,'Subject','email_subject'" in queue
    assert "formField(form,'Description / What We Need Quoted','description'" in queue
    assert "rfqApi('/config')" in queue
    assert 'Attachments · Photos / Drawings / PDFs' in queue
    assert "values.quantity=1;values.notes='';values.email_message='';" in queue
    assert "['email_subject','Email Subject'" in form
    assert "['description','Description / What We Need Quoted'" in form
    assert "fetchJSON('/pds-supplier-quotes/config')" in form
    assert "'/pds-supplier-quotes'" in form
    assert "@router.get('/config')" in RFQ
    assert 'PDS_SUPPLIER_QUOTES_REPLY_TO' in RFQ
    assert "@router.post('/{quote_id}/send')" in RFQ
    assert "row['status'] = 'send_uncertain'" in RFQ


def test_personal_badge_excludes_unassigned_office_queue():
    badges=section('async function refreshBadges()', 'function formsOf(')
    assert 'const myInvoices=officeInvoiceToDoJobs(jobs).filter(job=>' in badges
    assert "job.invoice_assigned_to||job.invoice_assignee||job.office_assigned_to" in badges
    assert "return !!owner && (mine.has(owner)||mine.has(resolved));" in badges
    assert 'count = new Set([...assignedQuotes,...myInvoices]' in badges
    assert 'const invoiceQueue=officeInvoiceToDoJobs(jobs)' in JS


def test_calendar_capacity_and_save_status_at_bottom_center():
    assert 'height:clamp(230px, 27vh, 300px)' in CSS
    assert 'Math.floor((available - markerHeight + gap) / rowSpace)' in JS
    notice=section('function pdsSaveNotice(', 'function pdsIsSaveRequest(')
    assert 'bottom:max(22px,env(safe-area-inset-bottom))' in notice
    assert 'left:50%;transform:translateX(-50%)' in notice
    assert 'top:92px;right:18px' not in notice
    assert "state==='error'" in notice
    assert 'pdsSaveNoticePending' in JS and 'pdsSaveNoticeFailed' in JS
    assert "pdsSaveNotice(completionWarnings?'Saved with warnings':'Saved!'" in JS


def test_shared_existing_green_feedback_bar_is_used_for_saves():
    feedback=(ROOT/'static/doorks_operation_feedback.js').read_text()
    ui=(ROOT/'templates/ui.html').read_text()
    assert 'doorks-operation-feedback' in feedback
    assert 'window.DoorksOperationFeedback' in feedback
    assert 'updateSave(label,state' in feedback
    assert 'if (init && init.__doorksManagedSave)' in feedback
    assert 'Request completed. Check the form for confirmation.' not in feedback
    assert 'doorks_operation_feedback.js?v=MOSES_5_57' in ui
    assert 'if(window.DoorksOperationFeedback?.updateSave)' in JS
    assert 'opts.__doorksManagedSave=true' in JS
    assert 'window.DoorksOperationFeedback.updateSave(message,kind' in JS
