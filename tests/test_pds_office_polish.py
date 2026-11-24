from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_pds_ticket_and_new_dispatch_use_sections():
    source=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert "card.className = \"card pds-office-intake\"" in source
    assert "card.className = \"card pds-office-ticket\"" in source
    assert "section('Customer & service location'" in source
    assert "section('Work details & references'" in source
    assert "ticketHeading.textContent='Job & contact information'" in source
    assert 'pdsLoadOfficePolish()' in source

def test_ui_preserves_existing_handlers_and_five_inline_fields():
    source=(ROOT/'static/app.js').read_text(encoding='utf-8')
    for marker in ['apiUpdateJob(job.id',"'po_number'","'estimate_number'","'sent_quote_number'","'quote_assigned_to'","'invoice_number'"]:
        assert marker in source
    assert 'Quick Edit Ticket Details' not in source
    assert 'follow.textContent = "Create Follow-Up Job"' not in source

def test_pds_business_hub_reuses_existing_ledger():
    source=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert 'className=\'card pds-office-business-hub\'' in source
    assert "renderManualAccountingLedger('pds','bills')" in source
    assert (ROOT/'static/pds_office_ticket_polish.css').is_file()


def test_pds_ticket_quick_date_uses_existing_api_and_receipt_label():
    source=(ROOT/'static/app.js').read_text(encoding='utf-8')
    assert "label.textContent='Receipt Upload'" in source
    assert "label.textContent='Records Upload'" not in source
    assert "dateInput.setAttribute('aria-label', 'Edit PDS dispatch scheduled date')" in source
    assert "['dispatch', 'sales_lead'].includes(String(job.kind" in source
    assert 'apiUpdateJob(job.id, { date: newDate, scheduled_date: newDate })' in source
    assert 'String(updated.date) !== newDate' in source
    assert 'String(updated.scheduled_date) !== newDate' in source
    assert "dateSave.textContent = 'Save date'" in source
