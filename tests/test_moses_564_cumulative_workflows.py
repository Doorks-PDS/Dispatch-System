"""Regression for the 5.64 repair release. No production records or provider sends."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'static' / 'app.js'
CALENDAR = ROOT / 'app' / 'routers' / 'calendar.py'


def _app():
    return APP.read_text(encoding='utf-8')


def test_original_alternate_menu_reuses_five_document_uploads():
    text = _app()
    assert "alternateUpload.textContent='Alternate'" in text
    assert "['Estimate','estimate']" in text
    assert "['Invoice','invoice']" in text
    assert "['Purchase Order','purchase_order']" in text
    assert "['Receipt','Receipt']" in text
    assert "['Packing Slip','Packing Slip']" in text


def test_new_part_action_shared_between_ticket_and_moses():
    text = _app()
    assert "card.querySelector('#helper_new_part').onclick=async()=>" in text
    assert "pdsQuickCatalogEditor('part'" in text


def test_po_editor_prefills_once_and_matches_verified_job_and_supplier_cost():
    text = _app()
    assert "if((isPds&&window.__pdsJobPODraft)||openNew)edit(null)" in text
    assert "await reload(); // editor opened once above" in text
    assert "customerSearch.value=item?.customer||form.elements.customer.value||''" in text
    assert "part.supplier_cost??part.supplier_rate??part.supplier_price" in text
    assert "Choose a unique saved PDS job number" in text
    assert "data.work_order=data.work_order_number" in text
    assert "data.job_id=data.work_order_number?form.dataset.linkedJobId||'':''" in text


def test_receipt_ai_remains_active_and_authorization_is_prominent():
    text = _app()
    assert "uploadForm.elements.file.addEventListener(\"change\",async()=>" in text
    assert 'const response=await fetch("/receipts/extract"' in text
    assert 'uploadReceipt.textContent="Upload Receipt / Read with AI"' not in text
    assert "pendingAction.textContent='🔔 Authorize ('" in text
    assert 'data.message||"AI did not return fields.' in text


def test_dispatch_and_sales_lead_quick_date_persists_both_fields():
    text = _app()
    assert "['dispatch', 'sales_lead'].includes(String(job.kind" in text
    assert "apiUpdateJob(job.id, { date: newDate, scheduled_date: newDate })" in text
    assert "buttons.append(savePlan, update);" in text
    source = CALENDAR.read_text(encoding='utf-8')
    assert "scheduled_date: Optional[str] = None" in source
    assert "scheduled_time: Optional[str] = None" in source


def test_email_templates_and_send_safeguards_not_replaced():
    source = _app()
    assert "heading.textContent = \"Review & Send \"" in source
    assert "Approve & Send via Resend" in source
    assert "Linked job number mismatch" in source


def test_accounting_exports_and_authorization_not_obscured():
    text = _app()
    assert "exportBtn.textContent = \"⬇ Export CSV\"" in text
    assert "authorization_status==='Authorized'" in text
