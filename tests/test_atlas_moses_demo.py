"""Public Moses Q&A is explicitly a guided local-only demo, not a live AI endpoint."""
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]

def test_demo_rendered_without_removing_lead_form():
    text=(BASE/'static/sdc_software.html').read_text(encoding='utf-8')
    assert 'id="atlas-moses-demo"' in text
    assert 'id="atlas-moses-workflows"' in text
    assert text.index('id="atlas-moses-demo"') < text.index('id="atlas-moses-workflows"')
    assert 'id="lead"' in text and '/api/software/inquiries' in text
    assert 'id="packages"' in text
    assert '/static/atlas_moses_demo.js' in text and '/static/atlas_moses_demo.css' in text
    assert 'No business records accessed' in text
    assert 'not sent to Atlas' in text

def test_public_demo_is_not_network_connected_or_actionable():
    js=(BASE/'static/atlas_moses_demo.js').read_text(encoding='utf-8')
    for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket(', 'localStorage', 'sessionStorage', 'eval(', 'innerHTML', '/api/'):
        assert forbidden not in js
    for topic in ('quote','invoice','permission','purchase','plan','work-order'):
        assert topic in js
    assert "p.textContent=content" in js
