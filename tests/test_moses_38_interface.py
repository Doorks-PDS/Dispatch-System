"""Moses 3.8 interface contract; existing records are not changed by UI controls."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "static/app.js").read_text()
CENTER = (ROOT / "static/moses_action_center.js").read_text()
UI = (ROOT / "templates/ui.html").read_text()

def test_expand_scroll_voice_and_no_duplicate_quote_button():
    assert "moses-chat-expanded" in APP
    assert "max-height:none!important;overflow-y:auto!important" in APP
    assert "compose.append(suggestions,composeLabel,input,voiceControls,composeRow)" in APP
    assert "Review PDS quotes';quoteTriageBtn" not in APP
    assert "moses-launch-glow{margin-right:9px" in APP

def test_action_center_is_collapsible_and_scrollable():
    assert "const section = document.createElement('details')" in CENTER
    assert "overflow-y:auto" in CENTER
    assert "panel.classList.toggle('moses-action-view'" in CENTER
    assert "Prepare invoice" in CENTER and "Prepare estimate" in CENTER

def test_quote_parts_review_does_not_send_or_save():
    assert "function openPdsQuotePartsReview(job)" in APP
    assert "new_door" in APP and "replacement_part" in APP
    assert "do not invent a cost" in APP
    assert "Do not send emails, alter job records or issue an estimate without approval" in APP
    assert "partsBtn.textContent='Parts & Pricing'" not in APP
    assert "openEstimateInvoiceHelper(full,type,null,{mosesJobFlow:true,afterSave:reloadWorkQueue})" in APP

def test_ui_assets_versioned():
    assert '/static/app.js?v=__APP_ASSET_VERSION__' in UI
    assert '/static/moses_action_center.js?v=4' in UI


def test_approved_time_off_is_shown_above_jobs_without_mutations():
    start = APP.index("// Approved time off appears as a minimal calendar marker")
    end = APP.index("dayJobs.forEach(j =>", start)
    fragment = APP[start:end]
    assert "apiListTimeOff({limit: 5000, status: 'approved'})" in fragment
    assert "=== 'approved'" in fragment
    assert "from<=dt && dt<=through" in fragment
    assert "names.join(', ')+' Out'" in fragment
    assert "items.appendChild(marker)" in fragment
    assert "new Set(dayAbsences.map(" in fragment
    assert "openCalendarTimeOffDetails(dt,dayAbsences)" in fragment
    assert "apiUpdateTimeOff" not in fragment
    assert "apiCreateTimeOff" not in fragment
    assert "apiUpdateJob" not in fragment
