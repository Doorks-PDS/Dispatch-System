from pathlib import Path

ROUTER = Path(__file__).resolve().parents[1] / 'app/routers/doorks_portals.py'
APP = Path(__file__).resolve().parents[1] / 'static/app.js'


def test_operational_decisions_cannot_be_bypassed():
    source = ROUTER.read_text()
    assert 'Use the operational change decision workflow' in source
    assert "'approved_pending_application'" in source
    assert "item.get('status') != 'approved_pending_application'" in source


def test_application_confirmation_requires_source_identity():
    source = ROUTER.read_text()
    assert "expected != payload.source_record_id" in source
    assert "'mark_applied'" in source
    assert "applied_to_source=True" in source


def test_office_review_controls_wired():
    source = APP.read_text()
    assert "'/decision'" in source
    assert "'/mark-applied'" in source
    assert "$('dpSaveReview').disabled=operational" in source
