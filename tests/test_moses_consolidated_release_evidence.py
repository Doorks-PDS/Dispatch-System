"""One consolidated, offline release gate for storage, agent, Resend, Stripe and HTTP.

This suite intentionally does not claim live-provider, physical-browser, or Render
production verification.  No requests are sent to external systems.
"""
from pathlib import Path
import json

import pytest
from fastapi import HTTPException

from app.services import moses_release_gate, moses_email_transport, moses_stripe
from tests.test_moses_release_http_smoke import client_factory as _client_factory


@pytest.fixture
def isolated_client(_client_factory):
    return _client_factory


def test_all_workspace_http_release_checks_are_scoped(isolated_client, tmp_path):
    for space in ('pds', 'doorks', 'sdc'):
        client = isolated_client(space)
        for endpoint in ('agent-readiness', 'storage-readiness', 'release-readiness'):
            result = client.get(f'/doorks-assistant/{endpoint}')
            assert result.status_code == 200, (space, endpoint, result.text)
        report = client.get('/doorks-assistant/release-readiness').json()
        assert report['deployment_authorized'] is False
        assert report['production_end_to_end_verified'] is False
        assert report['actions_fully_disabled'] is True
        assert set(report['agents']) == {'pds', 'doorks', 'sdc'}
    assert not list(tmp_path.rglob('*.json'))


def test_storage_candidate_mount_is_aligned_but_live_durability_unproven(tmp_path, monkeypatch):
    # The live Dispatch-System disk mount is managed by the Render service,
    # not this repository's historical render.yaml Blueprint (which points
    # at /var/data and is intentionally excluded from the drop-in release).
    actual_render_mount = '/opt/render/project/src/data'  # verified read-only in Render
    monkeypatch.setenv('MOSES_EXPECTED_RENDER_DISK_MOUNT', actual_render_mount)
    for key in moses_release_gate.ACTION_FLAGS:
        monkeypatch.delenv(key, raising=False)
    result = moses_release_gate.assess(actual_render_mount)
    assert result['storage']['configured_path_under_expected_disk'] is True
    assert result['storage']['durability_verified'] is False
    assert result['deployment_authorized'] is False
    assert not list(tmp_path.iterdir())


def test_external_providers_fail_closed_without_live_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'resend')
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('MOSES_STRIPE_TEST_ENABLED', raising=False)
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    with pytest.raises(HTTPException) as email_error:
        moses_email_transport.ready('documents@prioritydoors.com')
    assert email_error.value.status_code == 503
    report = moses_release_gate.assess(str(tmp_path))
    assert report['email']['live_delivery_verified'] is False
    assert report['payments']['sandbox_payment_verified'] is False
    assert report['production_end_to_end_verified'] is False
    assert not list(tmp_path.iterdir())


def test_release_report_never_exposes_keys_or_claims_live_validation(monkeypatch, tmp_path):
    monkeypatch.setenv('RESEND_API_KEY', 're_secret_example_do_not_print')
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'resend')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'documents@prioritydoors.com')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_hidden_example')
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-private-hidden')
    report = moses_release_gate.assess(str(tmp_path))
    raw = json.dumps(report)
    assert 'secret_example' not in raw and 'sk-private-hidden' not in raw
    assert report['email']['live_delivery_verified'] is False
    assert report['payments']['sandbox_payment_verified'] is False
    assert report['deployment_authorized'] is False


def test_resend_and_stripe_sandbox_flow_in_one_isolated_run(tmp_path, monkeypatch):
    """Provider contracts together: fake HTTP, real approval/webhook service logic."""
    from tests.test_moses_stripe import setup, mock_session, signed, event
    from tests.test_moses_resend import configure, MSG

    request = setup(tmp_path, monkeypatch)
    mock_session(monkeypatch)
    proposal = moses_stripe.propose(request, 'doorks', 'inv1')['proposal']
    assert moses_stripe.decide(request, 'doorks', proposal['id'], True)['state'] == 'checkout_ready'

    configure(monkeypatch)
    class ProviderReply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_): return b'{"id":"email_mock_release"}'

    calls = []
    def fake_provider(http_request, timeout=None):
        calls.append(http_request)
        return ProviderReply()
    monkeypatch.setattr(moses_email_transport, 'urlopen', fake_provider)
    assert moses_email_transport.send_resend(MSG, b'%PDF-1.4 mock') == 'email_mock_release'
    assert len(calls) == 1
    assert calls[0].full_url == 'https://api.resend.com/emails'

    body, signature = signed(event(proposal['id']))
    assert moses_stripe.webhook(request, body, signature)['processed'] is True
    assert moses_stripe.webhook(request, body, signature)['duplicate'] is True
    # An external Stripe signal cannot silently rewrite the accounting invoice status.
    rows = json.loads((tmp_path / 'business_workspaces' / 'doorks' / 'estimates_invoices.json').read_text())
    assert rows[0]['status'] == 'Sent'
