"""Regression coverage for the public floating Moses assistant.

The previous guided inline demo was intentionally replaced. Keep the lead
form, package cards, and customer-data boundary intact.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def test_floating_moses_replaces_inline_demo_without_removing_lead_form():
    page = (BASE / "static/sdc_software.html").read_text(encoding="utf-8")
    assert 'id="atlas-moses-chat-widget"' in page
    assert 'data-moses-open' in page and 'data-moses-panel' in page
    assert '/static/atlas_moses_public.js' in page
    assert '/static/atlas_moses_public.css' in page
    assert 'id="atlas-moses-demo"' not in page
    assert 'id="atlas-moses-workflows"' in page
    assert 'id="lead"' in page and '/api/software/inquiries' in page
    assert 'id="packages"' in page


def test_public_moses_uses_public_product_endpoint_only():
    js = (BASE / "static/atlas_moses_public.js").read_text(encoding="utf-8")
    assert "/doorks-assistant/public/atlas-chat" in js
    assert "data-moses-log" in js
    assert 'content.textContent=body' in js
    for forbidden in (
        "/doorks-assistant/chat", "/butler/actions/", "/documents/estimate",
        "/calendar/jobs/", "/workspaces/", "localStorage", "sessionStorage",
        "eval(", "innerHTML",
    ):
        assert forbidden not in js
    assert (BASE / "static/atlas_moses_public.css").is_file()
