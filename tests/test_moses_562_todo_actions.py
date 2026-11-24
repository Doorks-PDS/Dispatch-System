"""5.62: PDS To-Do gives direct job, supplier and estimate/invoice actions.

Source-level and isolated pure policy tests. No email, document or RFQ is sent.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = (Path(__file__).resolve().parents[1] / 'static/app.js').read_text()


def section(a, b):
    start=APP.index(a)
    return APP[start:APP.index(b,start)]


def test_todo_shows_direct_actions_and_reuses_existing_verified_flows():
    text=section('function renderMyAssignments()', '// PDS office dispatch board.')
    assert "supplier.textContent='Request Supplier Quote'" in text
    assert "const isInvoice=heading==='Office Invoices To Review'" in text
    assert "if(!isInvoice){" in text
    assert 'pdsQuickSupplierQuoteRequest(job.job_number' in text
    assert "if(saved?.id)note.textContent='Supplier request saved as Draft.'" in text
    assert "draft.textContent='Draft '+noun" in text
    assert 'openEstimateInvoiceHelper(full,type,null' in text
    assert "edit.textContent='View/Edit '+noun" in text
    assert "email.textContent='Email '+noun" in text
    assert 'pdsJobFlowLinkedDocuments(job,documents,type)' in text
    assert 'openEstimateInvoiceEmail(doc,type,{onSent:officeTasks._refresh})' in text
    assert '◉ Moses' not in text
    assert 'apiUpdateJob(' not in text


def test_job_ticket_is_drawer_and_does_not_navigate_away():
    text=section('function renderMyAssignments()', '// PDS office dispatch board.')
    assert "openDrawer('Job Details'" in text
    assert 'renderJobDetails(local,full,{afterSave:refresh,afterDelete:refresh})' in text
    assert 'workspaceBody.replaceChildren(root)' in text
    assert 'officeTasks._refresh' in text


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js not installed')
def test_todo_type_selection_never_infers_invoice_from_quote_alone():
    helper=section('function pdsToDoDocumentTypes(', '// Personal work tickets;')
    code=helper+'''
      const examples=[
       [{status:'Quote'},false],
       [{status:'Complete/Quote'},false],
       [{status:'Complete/Quote'},true],
       [{status:'Complete'},true],
       [{status:'To Be Invoiced'},true]
      ];
      console.log(JSON.stringify(examples.map(([job,queue])=>pdsToDoDocumentTypes(job,queue))));
    '''
    out=subprocess.run(['node','-e',code],text=True,capture_output=True,check=True)
    assert json.loads(out.stdout)==[
        ['estimate'],['estimate','invoice'],['estimate','invoice'],['invoice'],['invoice']
    ]
