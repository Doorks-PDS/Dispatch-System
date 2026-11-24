"""5.54 source contracts and pure-JS helpers against saved record formats.

No customer/supplier data is loaded and no external action is taken.
"""
from pathlib import Path
import json
import shutil
import subprocess
import pytest

APP = Path(__file__).resolve().parents[1].joinpath('static/app.js').read_text(encoding='utf-8')


def js_section(start, end):
    i=APP.index(start)
    return APP[i:APP.index(end, i)]


def eval_helper(start, end, body):
    if not shutil.which('node'):
        pytest.skip('Node runtime unavailable')
    source = js_section(start, end)
    result = subprocess.run(['node', '-e', source+'\n'+body], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_work_queue_routes_to_shared_helper_and_supplier_rfq_queue():
    queue=js_section('async function openPdsJobFlowWorkQueue()', 'function renderJobFlowView(')
    assert "const kinds=[['quotes','Quotes'],['invoices','Invoices'],['pricing','Supplier Pricing']]" in queue
    assert "Request Supplier Quote" in queue
    assert "await reloadQuotes()" in queue
    assert "openEstimateInvoiceHelper(full,type,null,{mosesJobFlow:true,afterSave:reloadWorkQueue})" in queue
    assert "await apiGetJob(job.id)" in queue
    assert "apiUpdateJob(" not in queue
    assert "/resend" not in queue


def test_actual_saved_quote_only_matches_same_job():
    matches=eval_helper('function pdsLinkedEstimateCandidates(', 'function pdsFormPhotoCarousel(', '''
    const job={id:'j101',job_number:'1126-07',customer:'Customer A'};
    const docs=[
      {type:'estimate',filename:'a.pdf',job_id:'j101',number:'RE0111',customer:'Customer A'},
      {type:'estimate',filename:'b.pdf',job_id:'j999',job_number:'1126-07',number:'RE0112',customer:'Customer B'},
      {type:'estimate',filename:'c.pdf',job_number:'1126-07',number:'RE0113',customer:'Customer A'},
      {type:'invoice',filename:'d.pdf',job_id:'j101',number:'JS0022',customer:'Customer A'}
    ];
    console.log(JSON.stringify(pdsLinkedEstimateCandidates(job,docs).map(x=>x.number)));
    ''')
    assert matches == ['RE0111', 'RE0113']


def test_quoted_work_rewritten_only_as_reviewed_completed_work():
    result=eval_helper('function pdsCompletedInvoiceText(', 'function pdsLinkedEstimateCandidates(', '''
    console.log(JSON.stringify(pdsCompletedInvoiceText('Proposal Includes:\\nFurnish and install a closer\\nRemove and replace lockset\\nPlease allow 2 weeks')));
    ''')
    assert 'Furnished and installed a closer' in result
    assert 'Removed and replaced lockset' in result
    assert 'Please allow' not in result


def test_linked_quote_cost_lines_copied_without_helper_duplicates():
    editor=js_section('async function openEstimateInvoiceDrawer(', 'function pdsCompletedInvoiceText(')
    assert 'items=sourceLines.map(createDocLineItem)' in editor
    assert 'dom.work.value=pdsCompletedInvoiceText(invoiceSource.work)' in editor
    assert 'const current=pdsLinkedEstimateCandidates' in editor
    assert 'JSON.stringify(current.items||[])!==JSON.stringify(invoiceSource.items||[])' in editor
    helper=js_section('function openEstimateInvoiceHelper(', 'function openEstimateDrawer(')
    assert 'helperPrefill.tripQty=0;helperPrefill.fuelQty=0;helperPrefill.hours=0' in helper
    assert "helperPrefill.parts=[];helperPrefill.partsText='';helperPrefill.autoFill=false" in helper
    assert 'invoiceSourceEstimate:linkedEstimate||null' in helper
    assert "pdsQuickCatalogEditor('part',{jobNumber:job?.job_number||''})" in helper


def test_recommendation_photos_use_saved_attachment_ids_and_fullsize_viewer():
    gallery=js_section('function pdsFormPhotoCarousel(', 'function openEstimateInvoiceHelper(')
    assert 'form?.attachments' in gallery
    assert 'isImageFilename(f.filename)' in gallery
    assert 'buildCompletionAttachmentUrl(jobId,form.id,f.filename)' in gallery
    assert 'pdsCompactPhotoViewer(files' in gallery
    assert 'openAttachmentCarousel(files,index)' in js_section('function pdsCompactPhotoViewer(', 'function pdsFormPhotoCarousel(')
    viewer=js_section('function pdsCompactPhotoViewer(', 'function pdsFormPhotoCarousel(')
    assert 'Math.floor(index/3)*3' in viewer
    assert "previous.setAttribute('aria-label','Previous photo')" in viewer
    assert "next.setAttribute('aria-label','Next photo')" in viewer
    assert 'image.src=item.url' in viewer


def test_timeoff_single_clickable_pill_and_side_request_details():
    calendar=js_section('function renderCalendarView()', 'async function openNewDispatch(')
    assert "const dayAbsences = approvedAbsences.filter(request" in calendar
    assert 'new Set(dayAbsences.map(' in calendar
    assert 'names.join(\', \')+\' Out\'' in calendar
    assert 'openCalendarTimeOffDetails(dt,dayAbsences)' in calendar
    assert 'event.stopPropagation()' in calendar
    assert 'marker.dataset.allNames' in calendar
    assert 'pill.scrollWidth>pill.clientWidth' in calendar
    assert "String(r.status||'').toLowerCase()==='approved'" in calendar
    assert 'formatDisplayDate(entry.start_date)' in calendar
    assert 'entry.notes' in calendar
    assert 'apiUpdateTimeOff(' not in calendar
    assert 'apiCreateTimeOff(' not in calendar


def test_doc_creation_preserves_status_until_provider_accepted_send():
    editor=js_section('async function openEstimateInvoiceDrawer(', 'function pdsCompletedInvoiceText(')
    assert 'status: job.status || "Dispatch"' in editor
    assert 'sent_quote_number: job.sent_quote_number || ""' in editor
    assert 'invoice_number: docType === "invoice" ? newDocNumber' in editor
