"""5.56 focused regression contracts for PDS Moses Job Flow and To-Do badges.

Tests are source-level only; live uploads/Resend/browser interactions still need acceptance.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1].joinpath('static', 'app.js').read_text()


def section(start, end):
    idx=SRC.index(start)
    return SRC[idx:SRC.index(end,idx)]


def test_tab_order_and_invoice_no_supplier_request():
    q=section('async function openPdsJobFlowWorkQueue()', 'function renderJobFlowView(')
    assert "const kinds=[['quotes','Quotes'],['invoices','Invoices'],['pricing','Supplier Pricing']]" in q
    assert "if(active==='quotes')controls.append(action('Request Supplier Quote'" in q
    assert "pdsQuickSupplierQuoteRequest(job.job_number||''" in q
    assert "active='pricing';editing={job_number" not in q
    assert "const saved=await pdsQuickSupplierQuoteRequest" in q


def test_view_job_stacks_without_removing_editable_helper():
    drawer=section('function openDrawer(', 'async function apiListJobs(')
    helper=section('function openEstimateInvoiceHelper(', 'function openEstimateDrawer(')
    assert 'if (!options.stack)' in drawer
    assert "{stack:true}" in helper
    assert "jobOverlay.style.zIndex='11300'" in helper


def test_photos_include_job_and_form_attachments_in_one_helper():
    forms=section('function pdsFormPhotoCarousel(', 'function openEstimateInvoiceHelper(')
    helper=section('function openEstimateInvoiceHelper(', 'function openEstimateDrawer(')
    assert "form?.attachments" in forms
    assert "job?.attachments" in forms
    assert 'buildJobAttachmentUrl(job.id,file.filename)' in forms
    assert 'openAttachmentCarousel(files,index)' in forms
    assert 'const jobPhotos=pdsJobPhotoCarousel(job)' in helper
    assert 'sourceGallery.append(jobTitle,jobPhotos)' in helper


def test_new_part_opens_an_actual_approval_gated_supplier_draft_form():
    catalog=section('function pdsQuickCatalogEditor(', 'function pdsQuickSupplierQuoteRequest(')
    supplier=section('function pdsQuickSupplierQuoteRequest(', '// Send saved PDS estimates/invoices')
    assert "quoteLabel.textContent='Supplier Quote'" in catalog
    assert "request.textContent='+ Request Supplier Quote'" in catalog
    assert "data.supplier_quote_id=api.form.dataset.pdsSupplierQuoteId" in catalog
    assert "'/pds-supplier-quotes'" in supplier
    assert "'/attachments'" in supplier
    assert "['email_subject','Email Subject" in supplier
    assert 'Review the email in Supplier Pricing before sending.' in supplier
    assert "'/send'" not in supplier


def test_helper_does_not_have_discarded_instruction_sentence():
    helper=section('function openEstimateInvoiceHelper(', 'function openEstimateDrawer(')
    assert 'Search and click a part to add it. You can still add blank/special items in the editable estimate.' not in helper


def test_pds_visible_todo_badge_has_quotes_and_invoices():
    counter=section('async function refreshBadges()', 'function formsOf(')
    jobs=section('function assignedQuoteJobs(', 'function initialsForName(')
    assert 'id="badgeMyAssignments"' in SRC
    assert "document.getElementById('badgeMyAssignments')" in counter
    assert 'officeInvoiceToDoJobs(jobs)' in counter
    assert 'assignedQuoteJobs(jobs)' in counter
    assert "'/pds-scheduling/my-jobs'" in counter
    assert "!job.invoice_number" in jobs
    assert "['To Be Invoiced','Complete','Complete/Quote']" in jobs
    assert 'const invoiceQueue=officeInvoiceToDoJobs(jobs);' in SRC
