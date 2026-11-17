"""Moses 4.5: verified office work queues do not depend on failing LLM calls."""
from pathlib import Path

APP = Path(__file__).resolve().parents[1].joinpath('static/app.js').read_text()
DRAFTS = Path(__file__).resolve().parents[1].joinpath('static/moses_drafts.js').read_text()


def test_job_flow_button_opens_office_queue_not_failed_ai_chat():
    assert "batchBtn.onclick=()=>openPdsJobFlowWorkQueue()" in APP
    assert "async function openPdsJobFlowWorkQueue()" in APP
    assert "Review the PDS Job Flow. Identify unassigned Quote jobs" not in APP
    assert "const groups={quotes,invoices,parts}" in APP
    assert "if(activePlatform!=='pds'||currentUser?.role!=='office_admin')return" in APP


def test_todo_actions_use_existing_workflows_and_keep_job_id():
    assert "window.openMosesDrafts({jobId:String(job.id)})" in APP
    assert "await openEstimateInvoiceDrawer(full,'invoice')" in APP
    assert "Review this job for an estimate: " not in APP


def test_specific_draft_requires_a_click_and_prepares_exact_record():
    assert "const openDrafts=(options={})" in DRAFTS
    assert "focusJobId=String(options?.jobId||'')" in DRAFTS
    assert "const selected=rows.filter(item=>String(item.job_id)===focusJobId)" in DRAFTS
    assert "prepareOne.onclick=async()=>" in DRAFTS
    assert "request('/prepare-job','POST',{record_id:focusJobId})" in DRAFTS
    assert "prepareAllButton.hidden=!!focusJobId" in DRAFTS


def test_customer_directory_index_and_initial_render_limit():
    assert 'const contactsByCompany=new Map()' in APP
    assert 'const related=contactsByCompany.get(normalized(company))||[]' in APP
    assert 'matched++;if(shown++>=60)continue' in APP
    assert 'Search to find any customer or contact.' in APP


def test_direct_actions_do_not_auto_send_or_change_work_records():
    start = APP.index('async function openPdsJobFlowWorkQueue()')
    end = APP.index('function renderJobFlowView(', start)
    queue = APP[start:end]
    assert "apiListJobs({limit:5000})" in queue
    assert "openDrawer('Job Details'" in queue
    assert "openEstimateInvoiceDrawer(await apiGetJob(job.id),'invoice')" in queue
    assert "window.openMosesDrafts({jobId:String(job.id)})" in queue
    assert '/resend' not in queue
    assert 'apiUpdateJob(' not in queue
