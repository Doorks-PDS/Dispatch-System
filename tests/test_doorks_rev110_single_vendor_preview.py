from pathlib import Path
root=Path(__file__).resolve().parents[1]
portal=(root/'static/doorks_home.html').read_text()
shared=(root/'static/doorks_shared_ticket.js').read_text()
def test_vendor_has_one_shared_preview_and_no_duplicate_renderer():
    body=portal.split('function portalVendorGenerator(',1)[1].split('function portalDocumentDetails(',1)[0]
    assert 'const preview=editor.preview' in body
    assert 'renderDocument(preview,editor.draft(),{vendor:true})' in body
    assert "items.reduce((sum,i)" not in body
    assert 'const table=document.createElement' not in body
    assert 'editor.validate()' in body
    assert 'win.document.body.append(preview.cloneNode(true))' in body

def test_reference_edits_invalidate_shared_preview():
    assert "reference.addEventListener('input',()=>{preview.hidden=true" in shared
