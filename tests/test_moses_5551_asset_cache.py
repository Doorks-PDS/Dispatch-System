"""Prevent stale application assets after a source deployment."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_ui_renders_fingerprinted_assets_and_noncacheable_html():
    import main

    response = main.ui(None)
    html = response.body.decode('utf-8')
    assert response.headers['cache-control'] == 'no-store'
    for filename in ('app.js', 'style.css'):
        expected = hashlib.sha256((ROOT / 'static' / filename).read_bytes()).hexdigest()[:12]
        assert f'/static/{filename}?v={expected}' in html
    assert '__APP_ASSET_VERSION__' not in html
    assert '__CSS_ASSET_VERSION__' not in html
    assert 'MOSES_5_48' not in html


def test_sidebar_badge_does_not_shift_subtitle():
    css = (ROOT / 'static/style.css').read_text()
    assert '.navbtn:has(>small){display:flex;flex-direction:row;' in css
    assert '.navbtn:has(>.badge){padding-right:52px;}' in css
    assert 'line-height:1.3;text-align:right;' in css
