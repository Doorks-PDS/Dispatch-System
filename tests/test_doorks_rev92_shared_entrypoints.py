"""Rev 92 shared role-aware entry point checks (no server permissions inferred)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_shared_entrypoints_and_role_guards():
    source = (ROOT / 'static/doorks_shared_ticket.js').read_text()
    assert 'function openTicket(context={})' in source
    assert 'function openDocument(context={})' in source
    assert 'function registerOfficeControllers(controllers)' in source
    assert "throw Error('Document editing is not permitted for this role')" in source
    assert "throw Error('Office document controller is not registered')" in source


def test_office_builder_kept_and_portal_uses_shared_entrypoints():
    office = (ROOT / 'static/app.js').read_text()
    portal = (ROOT / 'static/doorks_home.html').read_text()
    assert 'function openEstimateInvoiceDrawer(' in office
    assert 'function renderJobDetails(' in office
    assert 'registerOfficeControllers({' in office
    assert 'DoorksSharedTicket.openTicket({' in portal
    assert "DoorksSharedTicket.openDocument({role:'vendor'" in portal


def test_js_syntax():
    for file in ['static/app.js', 'static/doorks_shared_ticket.js']:
        subprocess.run(['node', '--check', str(ROOT / file)], check=True, capture_output=True)
