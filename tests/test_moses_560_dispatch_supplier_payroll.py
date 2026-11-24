"""5.60: supplier mail remains human-readable; payroll cannot skip its PIN via click events."""
from pathlib import Path

from app.routers.pds_supplier_quotes import _email_details, _safe_subject

ROOT = Path(__file__).parents[1]


def test_supplier_email_never_leaks_internal_job_number_or_imposes_quantity():
    row = {
        'job_number': '0926-79', 'quantity': 1,
        'description': 'Two storefront closers, left and right handing',
        'notes': '', 'email_message': '', 'email_subject': '',
    }
    text = _email_details(row, 'Example Supplier')
    assert 'Hello Example Supplier,' in text
    assert 'Two storefront closers, left and right handing' in text
    assert '0926-79' not in text
    assert 'Job:' not in text
    assert '1 ×' not in text
    assert '1 x' not in text
    assert _safe_subject(row) == 'PDS Supplier Pricing Request'
    assert row['job_number'] == '0926-79'  # still linked internally
    assert row['quantity'] == 1  # historical record metadata remains intact


def test_supplier_notes_and_custom_message_are_kept():
    row = {'description': 'Quote these hinges', 'quantity': 5,
           'notes': 'Stainless finish', 'email_message': 'Please send pricing by Friday.',
           'job_number': 'internal', 'email_subject': 'Requested pricing'}
    text = _email_details(row, 'Supplier')
    assert 'Stainless finish' in text
    assert 'Please send pricing by Friday.' in text
    assert '5 ×' not in text
    assert _safe_subject(row) == 'Requested pricing'


def test_payroll_navigation_requires_real_pin_confirmation_not_mouse_event():
    js = (ROOT / 'static/app.js').read_text()
    assert 'if(reportPinVerified !== true)' in js
    assert 'ensurePdsOfficeReportPin("Payroll", true)' in js
    assert 'if(access.unlocked && !promptEveryTime)return true;' in js
    assert 'navPayroll.addEventListener("click", () => renderPayrollView())' in js
    assert 'navPayroll.addEventListener("click", renderPayrollView)' not in js
    # The server verifies the PIN: it is never compared in front-end Javascript.
    server = (ROOT / 'app/routers/pds_office_reports.py').read_text()
    assert 'os.getenv("PDS_OFFICE_REPORT_PIN", "2005")' in server
    assert 'hmac.compare_digest(payload.pin, expected)' in server
