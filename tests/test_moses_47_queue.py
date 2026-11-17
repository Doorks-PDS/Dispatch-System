from pathlib import Path
APP=Path(__file__).resolve().parents[1].joinpath("static/app.js").read_text()
DRAFTS=Path(__file__).resolve().parents[1].joinpath("static/moses_drafts.js").read_text()

def test_queue_excludes_parts_on_order():
    assert "const parts=jobs.filter(j=>['quote','complete/quote','to be quoted','to be invoiced','complete']" in APP

def test_parts_review_links_to_actual_saved_draft():
    assert "draft.textContent='Add to Quote Draft'" in APP
    assert "window.openMosesDrafts({jobId:String(job.id),prepareIfMissing:true})" in APP

def test_status_uses_platform_pill():
    assert "const statusChip=statusPill(String(job.status||'Dispatch'))" in APP

def test_import_destinations_preview_only_without_commit():
    assert '<option value="service_vendors">Service Vendors — Preview</option>' in APP
    assert "!['vendors','parts'].includes(qbKind.value)" in APP

def test_drafts_search_and_compact():
    assert "search.placeholder='Search customer, job # or status'" in DRAFTS
    assert "-webkit-line-clamp:2" in DRAFTS

def test_drafts_initialization_declares_all_state():
    assert "let panel,body,feedback,prepareAllButton,focusJobId=''" in DRAFTS

def test_part_selection_routes_to_draft_editor_without_silent_save():
    assert "partNumber:chosenPartNumber" in APP
    assert "openEditor(draft)" in DRAFTS
    assert "{part_number:number,quantity:1}" in DRAFTS
