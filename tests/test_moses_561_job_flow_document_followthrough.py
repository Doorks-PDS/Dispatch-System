"""5.61: saved PDS documents remain in Moses Job Flow until approved sends.

Source-level tests and isolated status-sync tests; never contact Resend.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import shutil
import subprocess
import pytest

from app.services.moses_pds_document_email import _sync_sent_document_status

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static/app.js').read_text()
EMAIL = (ROOT / 'app/services/moses_pds_document_email.py').read_text()


def section(start, end):
    a = APP.index(start)
    return APP[a:APP.index(end, a)]


def test_job_flow_shows_saved_documents_not_second_draft():
    queue = section('async function openPdsJobFlowWorkQueue()', 'function renderJobFlowView(')
    assert "documents=loadedDocuments" in queue
    assert 'apiListDocuments()' in queue
    assert "const saved=pdsJobFlowLinkedDocuments(job,documents,type)" in queue
    assert "action('View/Edit'" in queue
    assert "action('Email'" in queue
    assert "openEstimateInvoiceEmail(doc,type," in queue
    assert "{mosesJobFlow:true,refreshDocs:reloadWorkQueue}" in queue
    assert "{mosesJobFlow:true,afterSave:reloadWorkQueue}" in queue
    assert "!j.invoice_number" not in queue
    assert 'if(saved.length)' in queue and '}else{' in queue
    assert "active==='quotes'?'Draft Estimate':'Draft Invoice'" in queue
    assert "apiUpdateJob(" not in queue


def test_saved_docs_bound_to_correct_customer_and_job_identity():
    if not shutil.which('node'):
        pytest.skip('node not installed')
    code = section('function pdsJobFlowLinkedDocuments(', '// Office work queue:')
    setup = '''
      const job={id:'job-1',job_number:'1126-15',customer:'North Italia'};
      const documents=[
        {type:'estimate',number:'RE00090',filename:'RE00090.pdf',job_id:'job-1',job_number:'1126-15',customer:'North Italia'},
        {type:'estimate',number:'RE00091',filename:'RE00091.pdf',job_id:'job-2',job_number:'1126-15',customer:'North Italia'},
        {type:'estimate',number:'RE00092',filename:'RE00092.pdf',job_id:'job-1',job_number:'1126-15',customer:'Other Customer'},
        {type:'estimate',number:'RE00093',filename:'RE00093.pdf',job_number:'1126-15',customer:'North Italia'},
        {type:'invoice',number:'JS00022',filename:'JS00022.pdf',job_id:'job-1',job_number:'1126-15',customer:'North Italia'},
        {type:'invoice',number:'JS00023',filename:'JS00023.pdf',job_id:'job-2',job_number:'1126-15',customer:'North Italia'},
        {type:'invoice',number:'JS00024',filename:'JS00024.pdf',job_id:'job-1',job_number:'wrong',customer:'North Italia'},
        {type:'invoice',number:'JS00025',filename:'JS00025.pdf',job_id:'job-1',job_number:'1126-15',customer:'North Italia',_read_only_pdf_fallback:true},
      ];
      console.log(JSON.stringify({estimate:pdsJobFlowLinkedDocuments(job,documents,'estimate').map(x=>x.number),invoice:pdsJobFlowLinkedDocuments(job,documents,'invoice').map(x=>x.number)}));
    '''
    p = subprocess.run(['node', '-e', code + '\n' + setup], capture_output=True, text=True, check=True)
    assert json.loads(p.stdout) == {'estimate': ['RE00090', 'RE00093'], 'invoice': ['JS00022']}


class FakeCalendarStore:
    def __init__(self, status, sent_quote_number='', estimate_number='RE00001'):
        self.job = {'id': 'job-1', 'job_number': '1126-15', 'status': status,
                    'sent_quote_number': sent_quote_number, 'estimate_number': estimate_number}
        self.writes = []

    def get_job(self, id):
        assert id == 'job-1'
        return dict(self.job)

    def update_job(self, id, payload):
        assert id == 'job-1'
        self.writes.append(dict(payload))
        self.job.update(payload)
        return dict(self.job)


def send(kind, status, sent_quote_number=''):
    store = FakeCalendarStore(status, sent_quote_number)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(calendar_store=store)))
    snapshot = {'job_id': 'job-1', 'job_number': '1126-15', 'number': 'RE00101' if kind == 'estimate' else 'JS00101', 'kind': kind}
    return store, _sync_sent_document_status(req, snapshot)


@pytest.mark.parametrize('status', ['Quote', 'Complete/Quote', 'To Be Quoted'])
def test_confirmed_estimate_sets_sent_status_and_sent_number_without_overwriting_original(status):
    store, result = send('estimate', status)
    assert result == 'Quote Sent'
    assert store.job['sent_quote_number'] == 'RE00101'
    assert store.job['estimate_number'] == 'RE00001'
    assert store.writes == [{'sent_quote_number': 'RE00101', 'status': 'Quote Sent'}]


def test_previous_sent_estimate_is_not_overwritten():
    store, result = send('estimate', 'Quote', 'RE00020')
    assert result == 'Quote Sent'
    assert store.job['sent_quote_number'] == 'RE00020'
    assert store.writes == [{'status': 'Quote Sent'}]


@pytest.mark.parametrize('status', ['Complete', 'Complete/Quote', 'To Be Invoiced'])
def test_confirmed_invoice_sets_done(status):
    store, result = send('invoice', status)
    assert result == 'Done'
    assert store.writes == [{'status': 'Done'}]


@pytest.mark.parametrize('status', ['Dispatch', 'Scheduled', 'Quote', 'Quote Sent', 'Done'])
def test_invoice_never_falsely_completes_ongoing_work(status):
    store, result = send('invoice', status)
    assert result == status
    assert store.writes == []


def test_sending_requires_approved_resend_confirmation_and_contact():
    assert "row.update(state='sent'" in EMAIL
    assert EMAIL.index("row.update(state='sent'") < EMAIL.index('_sync_sent_document_status(request, snap)')
    assert "'contact_email'" in EMAIL and "job.get('contact_email')" in EMAIL
    assert "MOSES_PDS_DOCUMENT_SEND_ENABLED" in EMAIL
    email_ui = section('async function openEstimateInvoiceEmail(', 'function exportEstimateInvoiceToQuickBooksCSV(')
    assert 'options.onSent' in email_ui
    assert 'status_sync === "verified"' in email_ui
