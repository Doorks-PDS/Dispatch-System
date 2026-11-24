from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
STORE = (ROOT / 'app/services/calendar_store.py').read_text(encoding='utf-8')
EMAIL = (ROOT / 'app/services/moses_pds_document_email.py').read_text(encoding='utf-8')

def test_purchase_orders_share_existing_documents_section():
    start = APP.index('function renderDocumentsSection(job)')
    end = APP.index('function renderSavedForms(', start)
    section = APP[start:end]
    assert 'Estimates, Invoices & Purchase Orders' in section
    assert "fetchJSON('/pds-purchase-orders')" in section
    assert "apiListDocuments({ job_id: job.id })" in section
    assert "po.work_order || po.work_order_number" in section
    assert "open.textContent = 'View PO'" in section
    assert "heading.textContent='Linked Purchase Orders'" not in APP

def test_schedule_uses_five_compact_weekday_columns_and_view_job_drawer():
    assert "weekends.checked?7:5" in APP
    assert "open.textContent='View Job'" in APP
    assert "openDrawer('Job Details'" in APP
    assert "open.textContent='Open ticket'" not in APP

def test_job_flow_unified_moses_prompt_and_approved_status_rules():
    assert "Moses — Job Flow assistant" in APP
    assert "batchBtn.onclick=()=>openPdsJobFlowWorkQueue()" in APP
    assert "current not in {'Quote', 'Complete/Quote', 'To Be Quoted'}" in EMAIL
    assert "row.update(state='sent'" in EMAIL
    assert "_sync_sent_document_status(request, snap)" in EMAIL
    assert "target = 'Quote Sent'" in EMAIL
    assert "target = 'Done'" in EMAIL
    assert 'has_recommendation' in STORE
