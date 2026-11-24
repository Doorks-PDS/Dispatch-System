"""Moses 5.63: Action Center shares Job Flow actions without replacing its secure backends.

Source UI contract + isolated JavaScript event test. No production writes, email or SMS.
"""
from pathlib import Path
import json
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
CENTER = (ROOT / 'static/moses_action_center.js').read_text()
APP = (ROOT / 'static/app.js').read_text()
UI = (ROOT / 'templates/ui.html').read_text()


def test_action_center_is_clean_tabs_and_visible_cards_not_dropdown_sections():
    assert "tabs.setAttribute('aria-label','Moses action queues')" in CENTER
    assert "const kinds=workspace==='pds'?['work','draft','approval','delivery','sms']" in CENTER
    assert 'moses-center-card' in CENTER
    assert "section.dataset.mosesTab=actionType" in CENTER
    assert "section = document.createElement('details')" not in CENTER
    assert "text('summary'" not in CENTER
    assert "Open Full Job Flow" in CENTER
    assert "search.addEventListener('input',filterCards)" in CENTER
    assert '/static/moses_action_center.js?v=5' in UI
    assert 'max-height:calc(100dvh - 28px)' in CENTER


def test_action_center_jobs_keep_all_direct_actions_and_workspace_bounds():
    assert "document.dispatchEvent(new CustomEvent('moses-open-pds-job'" in CENTER
    assert "new CustomEvent('moses-open-pds-job-flow'" in CENTER
    assert "new CustomEvent('moses-open-pds-jobflow-action'" in CENTER
    assert "run('supplier','Request Supplier Quote')" in CENTER
    assert "run('estimate','Estimate',true)" in CENTER
    assert "run('invoice','Invoice',true)" in CENTER
    assert 'if(isQuote||needsParts)' in CENTER
    assert 'if(isInvoice)' in CENTER
    assert 'if (isQuote) {' in CENTER  # Separate scope tools retained
    assert 'Review existing approvals' in CENTER
    assert 'moses-open-pds-jobflow-action' in APP
    assert "pdsJobFlowLinkedDocuments(job,docs,choice)" in APP
    assert "if(saved.length)" in APP
    assert "openEstimateInvoiceDrawer({...job,__docEdit:saved[0]}" in APP
    assert "openEstimateInvoiceHelper(job,choice,null,{mosesJobFlow:true})" in APP
    assert 'PDS_SMS_SEND_ENABLED' not in CENTER  # Existing backend, not client, owns the send gate.


@pytest.mark.skipif(not shutil.which('node'), reason='Node not installed')
def test_action_event_reuses_saved_document_and_never_sends_or_creates_without_user_action():
    start = APP.index("  document.addEventListener('moses-open-pds-job-flow', () => {")
    end = APP.index('  // Moses draft review links', start)
    handlers = APP[start:end]
    code = r'''
      const calls=[];
      const handlers={};
      const document={addEventListener:(name,cb)=>{handlers[name]=cb}};
      let activePlatform='pds';let currentUser={role:'office_admin'};
      const saved={type:'estimate',number:'RE00099',job_id:'j123',customer:'Example'};
      let docs=[saved],job={id:'j123',job_number:'1126-01',customer:'Example',status:'Quote'};
      const apiGetJob=async id=>job;
      const apiListDocuments=async ()=>docs;
      const pdsJobFlowLinkedDocuments=(j,rows,type)=>rows.filter(r=>r.type===type);
      const pdsQuickSupplierQuoteRequest=async (...args)=>{calls.push(['supplier',args]);return {id:'draft1'}};
      const openEstimateInvoiceDrawer=(...args)=>calls.push(['editor',args]);
      const openEstimateInvoiceHelper=(...args)=>calls.push(['helper',args]);
      const openPdsJobFlowWorkQueue=()=>calls.push(['full']);
      const alert=msg=>calls.push(['alert',msg]);
    ''' + handlers + r'''
      (async()=>{
        handlers['moses-open-pds-job-flow']();
        await handlers['moses-open-pds-jobflow-action']({detail:{job_id:'j123',action:'estimate'}});
        docs=[];
        await handlers['moses-open-pds-jobflow-action']({detail:{job_id:'j123',action:'invoice'}});
        await handlers['moses-open-pds-jobflow-action']({detail:{job_id:'j123',action:'supplier'}});
        const before=calls.length;
        await handlers['moses-open-pds-jobflow-action']({detail:{job_id:'../illegal',action:'estimate'}});
        activePlatform='sdc';
        await handlers['moses-open-pds-jobflow-action']({detail:{job_id:'j123',action:'estimate'}});
        console.log(JSON.stringify({kinds:calls.map(x=>x[0]),
          saved:calls[1][1][0].__docEdit.number,
          invoice:calls[2][1][1],
          supplierJob:calls[3][1][0],
          noChange:calls.length===before}));
      })().catch(e=>{console.error(e);process.exit(1)});
    '''
    result = subprocess.run(['node','-e',code], capture_output=True, text=True, check=True)
    outcome = json.loads(result.stdout)
    assert outcome == {
        'kinds': ['full','editor','helper','supplier'],
        'saved': 'RE00099',
        'invoice': 'invoice',
        'supplierJob': '1126-01',
        'noChange': True,
    }
