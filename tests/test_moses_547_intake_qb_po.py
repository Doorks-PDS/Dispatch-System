"""PDS Moses intake review and external purchase-order reference protection."""
from pathlib import Path
import json
import subprocess
import shutil
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_document_intake_requires_field_review_before_dispatch_save():
    js=(ROOT/'static/app.js').read_text()
    assert 'Review extracted work-order details' in js
    assert 'Apply selected details to dispatch form' in js
    assert "checked.type='checkbox'" in js
    assert 'Replace ${replacements.length} already populated field(s)' in js
    assert 'statusBox.textContent=`Moses extracted ${selections.length} suggested detail(s). Nothing has been saved.' in js
    # Extracted identity must go through the existing separate review component.
    assert 'window.MosesIdentityReview.mount' in js


def test_pds_po_create_and_import_are_distinct_actions():
    js=(ROOT/'static/app.js').read_text()
    assert "poButton.textContent='Purchase Order'" in js
    assert "alternateUpload.textContent='Alternate'" in js
    assert "renderDocumentVault('pds',type," in js
    assert "['Packing Slip','Packing Slip']" in js
    assert "form.elements.job_number.value=ref.job_number||''" in js
    assert "form.elements.document_number.value=ref.po_number||''" in js
    assert "if(!item&&platform==='pds'&&window.__pdsJobPODraft)" in js
    assert "if(canManagePO && ((isPds&&window.__pdsJobPODraft)||openNew))edit(null)" in js


def test_identity_review_finds_similar_saved_company_without_auto_selection():
    node=shutil.which('node')
    if not node:pytest.skip('node is not available')
    source=r"""
const match = require('./static/moses_identity_review.js');
const records = [{company_name:'The Irvine Company'}, {company_name:'Irvine Construction'}, {company_name:'North Italia'}];
const result=match.companyCandidates('Irvine Company',records);
if(result.length===0 || result[0].value !== 'The Irvine Company') process.exit(2);
if(result.some(x=>x.value==='North Italia'))process.exit(3);
console.log(JSON.stringify(result));
"""
    run=subprocess.run([node,'-e',source],cwd=ROOT,capture_output=True,text=True,check=True)
    found=json.loads(run.stdout)
    assert found[0]['value']=='The Irvine Company'
    script=(ROOT/'static/moses_identity_review.js').read_text()
    assert "customerSelect.value='';" in script
    assert 'Browse / search all saved PDS customers' in script
    assert 'Never select an address solely on similarity' in script
