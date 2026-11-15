"""Rev77 secure full-estimate PDF access tests (no production data)."""
import json
from io import BytesIO
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from app.services import moses_estimate_acceptance as acceptance
from app.routers.doorks_assistant import customer_estimate_pdf, MosesEstimatePdfRequest
from test_moses_estimate_acceptance import setup


def prepare(tmp_path, platform='doorks'):
    admin, public, folder = setup(tmp_path, platform)
    rows = json.loads((folder/'estimates_invoices.json').read_text())
    rows[0].update(line_items=json.dumps([
        {'description':'Service / door closer repair', 'quantity':2, 'rate':100, 'taxable':True},
        {'description':'Adjustment and testing', 'quantity':1, 'rate':50, 'taxable':False}]),
        tax_rate=0, tax_amount=0, amount=250, terms='Due on approval', notes='Repair scope confirmed')
    (folder/'estimates_invoices.json').write_text(json.dumps(rows))
    return admin, public, folder


@pytest.mark.parametrize('platform', ['doorks','sdc'])
def test_pdf_contains_actual_reviewed_line_items_and_is_private(tmp_path, platform):
    admin, public, folder = prepare(tmp_path, platform)
    token = acceptance.issue(admin, platform, 'estimate-1')['token']
    res = customer_estimate_pdf(MosesEstimatePdfRequest(token=token), public)
    assert res.status_code == 200
    assert res.headers['Cache-Control'] == 'no-store'
    assert res.headers['Content-Disposition'].startswith('attachment;')
    content = ''.join(page.extract_text() for page in PdfReader(BytesIO(res.body)).pages)
    for phrase in ['RE00076','Service / door closer repair','Adjustment and testing', '250.00','Due on approval']:
        assert phrase in content
    assert 'contact@example.com' not in content
    assert token.encode() not in res.body


def test_pdf_revoked_or_modified_estimate_fails_closed(tmp_path):
    admin,public,folder=prepare(tmp_path)
    link=acceptance.issue(admin,'doorks','estimate-1')
    rows=json.loads((folder/'estimates_invoices.json').read_text())
    rows[0]['line_items']=json.dumps([{'description':'Changed work', 'quantity':1,'rate':250}])
    (folder/'estimates_invoices.json').write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as err: acceptance.document_pdf(public,link['token'])
    assert err.value.status_code == 409
    acceptance.revoke(admin,'doorks',link['link_id'])
    with pytest.raises(HTTPException) as err: acceptance.document_pdf(public,link['token'])
    assert err.value.status_code == 410


def test_pdf_unreviewed_or_inconsistent_pricing_is_blocked(tmp_path):
    admin,public,folder=prepare(tmp_path)
    token=acceptance.issue(admin,'doorks','estimate-1')['token']
    rows=json.loads((folder/'estimates_invoices.json').read_text())
    rows[0]['line_items']=json.dumps([{'description':'Repair','quantity':1,'rate':500}])
    (folder/'estimates_invoices.json').write_text(json.dumps(rows))
    # Fingerprint catches tampering first.
    with pytest.raises(HTTPException): acceptance.document_pdf(public,token)
    # New link issued for an internally inconsistent estimate still cannot render.
    acceptance.revoke(admin,'doorks',json.loads((folder/'estimate_acceptance_links.json').read_text())[0]['id'])
    with pytest.raises(HTTPException) as err: acceptance.issue(admin,'doorks','estimate-1')
    assert err.value.status_code == 409


def test_page_requires_document_download_before_showing_form():
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'static'
    html=(path/'estimate_acceptance.html').read_text()
    js=(path/'estimate_acceptance.js').read_text()
    assert 'id="download-pdf"' in html
    assert "form.hidden = false;" in js
    assert js.index("form.hidden = false;") > js.index("pdfButton.addEventListener")
