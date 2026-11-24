from pathlib import Path
APP=Path(__file__).resolve().parents[1].joinpath("static/app.js").read_text()
DRAFTS=Path(__file__).resolve().parents[1].joinpath("static/moses_drafts.js").read_text()

def test_queue_uses_estimate_invoice_and_supplier_pricing():
    assert "const kinds=[['quotes','Quotes'],['invoices','Invoices'],['pricing','Supplier Pricing']]" in APP
    assert "const parts=jobs.filter(" not in APP
    assert "const invoices=jobs.filter(" in APP

def test_parts_review_links_to_actual_saved_draft():
    assert "draft.textContent='Add to Quote Draft'" in APP
    assert "window.openMosesDrafts({jobId:String(job.id),prepareIfMissing:true,partNumber:chosenPartNumber})" in APP

def test_status_uses_platform_pill():
    assert "const statusChip=statusPill(String(job.status||'Dispatch'))" in APP

def test_data_import_requires_explicit_preview_then_commit_for_supported_records():
    assert '<option value="service_vendors">Service Vendors — Import</option>' in APP
    assert 'importable_kinds' in APP and 'can_import_records' in APP
    assert "Review only for "+"'" in APP

def test_drafts_search_and_compact():
    assert "search.placeholder='Search customer, job # or status'" in DRAFTS
    assert "-webkit-line-clamp:2" in DRAFTS

def test_drafts_initialization_declares_all_state():
    assert "let panel,body,feedback,prepareAllButton,focusJobId=''" in DRAFTS

def test_part_selection_routes_to_draft_editor_without_silent_save():
    assert "partNumber:chosenPartNumber" in APP
    assert "openEditor(draft)" in DRAFTS
    assert "{part_number:number,quantity:1}" in DRAFTS

def test_office_hub_moves_ledger_to_accounting_only():
    assert "{icon:'💳',label:'Supplier Bills & Payments',description:'Review supplier bills and manual payments through the existing accounting ledger.'" not in APP
    assert "{id:'manual-ledger',icon:'🧾',label:'Supplier Bills & Payments'" in APP

def test_job_flow_draft_estimate_uses_saved_draft_or_regular_generator():
    assert "active==='quotes'?'Draft Estimate':'Draft Invoice'" in APP
    assert "const saved=await fetchJSON('/moses-drafts').catch(()=>({items:[]}))" in APP
    assert "await openEstimateInvoiceDrawer(full,'estimate')" in APP
    assert "window.openMosesDrafts({jobId:String(job.id)})" in APP

def test_draft_approval_opens_verified_estimator():
    assert "if(approved&&reply.item?.state==='ready_for_estimator')" in DRAFTS
    assert "new CustomEvent('moses-open-pds-estimator'" in DRAFTS
    assert "new CustomEvent('moses-open-pds-standard-estimator'" in DRAFTS
    assert "const handoff = await fetchJSON('/moses-drafts/'" in APP

def test_action_center_groups_followups():
    assert "const group=document.createElement('details')" in APP
    assert "followGroupHost=entries" in APP
