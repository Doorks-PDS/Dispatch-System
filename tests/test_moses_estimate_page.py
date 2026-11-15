"""Rev76: customer page stays public, minimal, and never auto-sends."""
from app.routers.doorks_assistant import customer_estimate_page
from app.services import moses_estimate_acceptance as acceptance
from test_moses_estimate_acceptance import setup


def test_page_has_restricted_headers_and_no_dynamic_token():
    response = customer_estimate_page()
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert "default-src 'none'" in response.headers['Content-Security-Policy']
    assert b'accept-form' in response.body
    assert b'final estimate provided to me' in response.body
    assert b'<script defer src="/static/estimate_acceptance.js"' in response.body


def test_page_link_uses_url_fragment_and_keeps_original_acceptance_rules(tmp_path):
    admin, public, folder = setup(tmp_path)
    created = acceptance.issue(admin, 'doorks', 'estimate-1')
    assert created['acceptance_path'].endswith('#' + created['token'])
    assert '/public/estimates/accept#' in created['acceptance_path']
    assert created['token'] not in (folder/'estimate_acceptance_links.json').read_text()
    assert acceptance.inspect(public, created['token'])['document_number'] == 'RE00076'
    assert acceptance.accept(public, created['token'], 'Taylor Client')['accepted']
