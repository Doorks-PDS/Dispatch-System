from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_shared_editor_validates_vendor_lines():
    shared=(ROOT/'static/doorks_shared_ticket.js').read_text()
    portal=(ROOT/'static/doorks_home.html').read_text()
    assert "if(role!=='vendor')throw Error" in shared
    assert 'Number.isFinite(qty)' in shared
    assert 'Number.isFinite(rate)' in shared
    assert 'editor.validate()' in portal
    assert 'validation.errors.join' in portal
