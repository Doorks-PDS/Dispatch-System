from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static/app.js').read_text()
DRAFTS = (ROOT / 'static/moses_drafts.js').read_text()
IMPORT = (ROOT / 'app/routers/pds_purchase_orders.py').read_text()


def test_quote_and_todo_use_record_backed_draft():
    assert 'openPdsSingleQuoteReview(job)' in APP
    assert 'prepareIfMissing:true' in APP
    assert "request('/prepare-job','POST',{record_id:focusJobId})" in DRAFTS
    assert 'if(prepareIfMissing)' in DRAFTS


def test_part_review_reads_verified_job_and_catalog():
    assert 'async function openPdsPartReview(job)' in APP
    assert 'await apiGetJob(job.id)' in APP
    assert 'apiListParts({q:query,limit:25})' in APP
    assert "draft.textContent='Add to Quote Draft'" in APP


def test_import_preview_separate_from_approved_write():
    assert "@router.post('/import/file-preview')" in IMPORT
    assert "_import_guard(request)" in IMPORT
    assert "await file.read(8 * 1024 * 1024 + 1)" in IMPORT
    assert "'can_import_supplier_parts':ext in ('.csv','.xlsx')" in IMPORT
    assert "@router.post('/import/commit')" in IMPORT
    assert "'/pds-purchase-orders/import/file-preview'" in APP
    assert 'qbCommit.disabled=!response.new_count||!!response.invalid_count;' in APP


def test_pds_document_intent_does_not_mistake_negation_for_send():
    spec=importlib.util.spec_from_file_location('intent',ROOT/'app/services/moses_pds_document_intent.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert not module.is_pds_document_mail_request('Review the quote and do not send emails')
    assert not module.is_pds_document_mail_request('Prepare a quote draft, do not email or send it')
    assert module.is_pds_document_mail_request('Send estimate RE00125 to customer')


def test_todo_status_present():
    assert "const statusChip=statusPill(String(job.status||'Dispatch'))" in APP
