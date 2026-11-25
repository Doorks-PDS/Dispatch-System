"""QuickBooks Hub 5.68: Office Admin only, no live posting or hidden sync."""
import json
from pathlib import Path
from fastapi import HTTPException
import pytest
from app.services import pds_quickbooks_bridge as qb
from app.routers import pds_quickbooks_bridge as router
from test_moses_567_quickbooks_handoff import setup_request

ROOT = Path(__file__).parents[1]

@pytest.mark.parametrize('role', ['tech', 'lead', 'office', 'admin', '', 'guest'])
def test_all_quickbooks_actions_denied_to_non_admin(tmp_path, role):
    req, _ = setup_request(tmp_path, 'office_admin')
    req.state.auth_role = role
    calls = [lambda: qb.status(req), lambda: qb.preview(req),
             lambda: qb.export_review_csv(req),
             lambda: qb.prepare(req, 'JS00021', 'a' * 64),
             lambda: qb.select_edition(req, 'online'),
             lambda: router.configuration(router.EditionSettings(edition='desktop', confirm=True), req)]
    for action in calls:
        with pytest.raises(HTTPException) as ex:
            action()
        assert ex.value.status_code == 403


def test_office_admin_setup_is_saved_but_never_connects(tmp_path, monkeypatch):
    monkeypatch.delenv('PDS_QUICKBOOKS_EDITION', raising=False)
    req, _ = setup_request(tmp_path)
    assert qb.status(req)['edition'] == 'not_selected'
    with pytest.raises(HTTPException) as ex:
        router.configuration(router.EditionSettings(edition='online', confirm=False), req)
    assert ex.value.status_code == 422
    saved = router.configuration(router.EditionSettings(edition='online', confirm=True), req)
    assert saved['edition'] == 'online'
    assert saved['connected_to_quickbooks'] is False
    assert saved['automatic_sync_enabled'] is False
    assert saved['payments_modified'] is False
    assert saved['inventory_modified'] is False
    assert qb.preview(req)['edition'] == 'online'
    path = tmp_path / 'pds_quickbooks_settings.json'
    assert json.loads(path.read_text())['edition'] == 'online'
    assert qb.select_edition(req, 'desktop')['edition'] == 'desktop'
    assert not (tmp_path / 'pds_quickbooks_invoice_handoff.json').exists()


def test_quickbooks_edition_env_override_is_not_written(tmp_path, monkeypatch):
    req, _ = setup_request(tmp_path)
    monkeypatch.setenv('PDS_QUICKBOOKS_EDITION', 'online')
    assert qb.status(req)['edition'] == 'online'
    with pytest.raises(HTTPException) as exc:
        qb.select_edition(req, 'desktop')
    assert exc.value.status_code == 409
    assert not (tmp_path / 'pds_quickbooks_settings.json').exists()


def test_invalid_config_does_not_silently_change_edition(tmp_path, monkeypatch):
    monkeypatch.delenv('PDS_QUICKBOOKS_EDITION', raising=False)
    req, _ = setup_request(tmp_path)
    (tmp_path / 'pds_quickbooks_settings.json').write_text('{bad JSON')
    with pytest.raises(HTTPException) as exc:
        qb.status(req)
    assert exc.value.status_code == 503


def test_admin_does_not_get_quickbooks_in_other_workspace(tmp_path):
    req, _ = setup_request(tmp_path)
    req.session['active_platform'] = 'doorks'
    for action in [lambda: qb.status(req), lambda: qb.preview(req), lambda: qb.export_review_csv(req)]:
        with pytest.raises(HTTPException) as exc:
            action()
        assert exc.value.status_code == 403


def test_quickbooks_hub_uses_sidebar_with_role_guard_and_no_real_sync_controls():
    app=(ROOT/'static/app.js').read_text()
    html=(ROOT/'templates/ui.html').read_text()
    css=(ROOT/'static/pds_quickbooks_hub.css').read_text()
    assert 'id="navQuickBooks"' in html
    assert html.index('id="navAccounting"') < html.index('id="navQuickBooks"') < html.index('id="navPayroll"')
    assert 'role === "office_admin" && activePlatform === "pds"' in app
    assert "activePlatform !== 'pds' || currentUser?.role !== 'office_admin'" in app
    assert "setNavActive(navQuickBooks)" in app
    for phrase in ['QuickBooks Hub', 'Invoice handoff', 'Handoff activity', 'Connection setup', 'Prepare handoff', 'Export review CSV']:
        assert phrase in app
    assert "'/pds-quickbooks/configuration'" in app
    assert "'/pds-quickbooks/prepare-invoice'" in app
    assert "connected_to_quickbooks': False" in (ROOT/'app/services/pds_quickbooks_bridge.py').read_text()
    assert '.qbh-hero' in css and '@media(max-width:610px)' in css
