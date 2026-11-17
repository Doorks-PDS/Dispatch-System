"""Regression contract for the PDS 4.0 interface and safe draft lifecycle."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
DRAFTS = (ROOT / 'static/moses_drafts.js').read_text(encoding='utf-8')
API = (ROOT / 'app/routers/moses_drafts.py').read_text(encoding='utf-8')


def test_pds_context_cards_are_white_with_subtle_outline():
    assert APP.count('border:1px solid #dbe3e9;border-radius:10px;background:#fff;margin:10px 0') == 2
    assert 'background:#fffaf5' not in APP


def test_staff_plan_compact_and_keeps_workspace_permissions():
    assert "caption.textContent='Technicians'" in APP
    assert "textContent='Date'" in APP
    assert "textContent='Time'" in APP
    assert "textContent='Reconnecting PDS…'" in APP
    assert "'/platforms/switch'" in APP
    assert "'/pds-scheduling/assignable-staff'" in APP


def test_draft_view_job_closes_overlay_and_review_is_reversible():
    assert "h('button','View Job','btn')" in DRAFTS
    assert "document.dispatchEvent(new CustomEvent('moses-open-pds-job'" in DRAFTS
    assert "topDrawer.style.zIndex='11250'" in APP
    assert "'/reopen'" in DRAFTS
    assert "'/archive'" in DRAFTS
    assert "item.get('state') not in ('ready_for_estimator', 'declined')" in API
    assert "@router.post('/{draft_id}/archive')" in API
    assert 'review_events=events[-30:]' in API


def test_accounting_export_reuses_approved_period_rows():
    assert "const authorized=periodReceipts.filter(r=>r.authorization_status==='Authorized')" in APP
    assert "Export expenditures CSV" in APP
    assert "columns=['date','employee','vendor','category','amount','receipt_number','notes']" in APP
    assert "escapeCsv(row[k])" in APP
    assert "section === \"overview\"" in APP
