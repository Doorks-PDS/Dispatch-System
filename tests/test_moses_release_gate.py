"""Readiness assessment must never authorize deployment or perform side effects."""
import json
from app.services import moses_release_gate


def test_gate_is_fail_closed_with_empty_config(tmp_path, monkeypatch):
    for key in ('OPENAI_API_KEY', 'RESEND_API_KEY', 'RESEND_WEBHOOK_SECRET',
                'MOSES_DOCUMENTS_FROM', 'STRIPE_SECRET_KEY', 'MOSES_STRIPE_TEST_ENABLED'):
        monkeypatch.delenv(key, raising=False)
    result = moses_release_gate.assess(str(tmp_path / 'missing'))
    assert not result['deployment_authorized']
    assert not result['storage']['directory_exists']
    assert len(result['release_blockers']) == 6
    assert not (tmp_path / 'missing').exists()


def test_gate_never_discloses_credentials_or_promises_delivery(tmp_path, monkeypatch):
    secret = 're_private_secret_do_not_echo'
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'resend')
    monkeypatch.setenv('RESEND_API_KEY', secret)
    monkeypatch.setenv('RESEND_WEBHOOK_SECRET', 'whsec_private_secret')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'documents@prioritydoors.com')
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-private-secret')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_private_secret')
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED', 'true')
    result = moses_release_gate.assess(str(tmp_path))
    raw = json.dumps(result)
    assert all(token not in raw for token in ('private_secret', secret, 'sk-private-secret'))
    assert result['email']['resend_key_configured']
    assert not result['email']['live_delivery_verified']
    assert not result['payments']['sandbox_payment_verified']
    assert not result['deployment_authorized']


def test_gate_covers_all_workspaces(tmp_path):
    result = moses_release_gate.assess(str(tmp_path))
    assert set(result['agents']) == {'pds', 'doorks', 'sdc'}


def test_gate_does_not_create_files(tmp_path):
    before = list(tmp_path.iterdir())
    moses_release_gate.assess(str(tmp_path))
    assert list(tmp_path.iterdir()) == before


def test_gate_flags_mismatched_render_mount(tmp_path, monkeypatch):
    monkeypatch.setenv('MOSES_EXPECTED_RENDER_DISK_MOUNT', str(tmp_path / 'mounted'))
    result = moses_release_gate.assess(str(tmp_path / 'wrong'))
    assert result['disk_mount_alignment_required'] is True
    assert result['storage']['disk_path_mismatch'] is True
    assert result['deployment_authorized'] is False
    assert not (tmp_path / 'mounted').exists()


def test_gate_does_not_certify_aligned_mount(tmp_path, monkeypatch):
    disk = tmp_path / 'mounted'
    monkeypatch.setenv('MOSES_EXPECTED_RENDER_DISK_MOUNT', str(disk))
    result = moses_release_gate.assess(str(disk))
    assert result['storage']['configured_path_under_expected_disk'] is True
    assert not result['deployment_authorized']


def test_gate_reports_all_live_action_flags_without_secrets(tmp_path, monkeypatch):
    for flag in moses_release_gate.ACTION_FLAGS:
        monkeypatch.delenv(flag, raising=False)
    inactive = moses_release_gate.assess(str(tmp_path))
    assert inactive['actions_fully_disabled'] is True
    assert inactive['enabled_external_or_write_actions'] == []
    monkeypatch.setenv('MOSES_PO_SEND_ENABLED', 'true')
    monkeypatch.setenv('MOSES_SUPPLIER_BILL_ACTIONS_ENABLED', 'true')
    flagged = moses_release_gate.assess(str(tmp_path))
    assert flagged['actions_fully_disabled'] is False
    assert set(flagged['enabled_external_or_write_actions']) == {
        'MOSES_PO_SEND_ENABLED', 'MOSES_SUPPLIER_BILL_ACTIONS_ENABLED'}
    assert flagged['deployment_authorized'] is False


def test_sms_gate_is_read_only_and_never_certifies_a2p(tmp_path, monkeypatch):
    for name in ('PDS_SMS_SEND_ENABLED', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
                 'PDS_TWILIO_NUMBER', 'PDS_SMS_PUBLIC_BASE_URL'):
        monkeypatch.delenv(name, raising=False)
    result = moses_release_gate.assess(str(tmp_path / 'uncreated'))
    sms = result['sms']
    assert not sms['outbound_enabled']
    assert not sms['provider_configuration_complete']
    assert not sms['a2p_approved_verified']
    assert not (tmp_path / 'uncreated').exists()


def test_sms_gate_does_not_expose_credentials_or_enable_sending(tmp_path, monkeypatch):
    monkeypatch.setenv('TWILIO_ACCOUNT_SID', 'AC' + 'a' * 32)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'sensitive_test_token')
    monkeypatch.setenv('PDS_TWILIO_NUMBER', '+17606421131')
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', 'https://example.test')
    monkeypatch.setenv('PDS_SMS_SEND_ENABLED', 'true')
    state = moses_release_gate.assess(str(tmp_path))
    assert state['sms']['provider_configuration_complete']
    assert state['sms']['outbound_enabled']
    assert not state['sms']['a2p_approved_verified']
    assert not state['sms']['end_to_end_delivery_verified']
    assert not state['deployment_authorized']
    assert 'sensitive_test_token' not in json.dumps(state)
    assert ('AC' + 'a' * 32) not in json.dumps(state)


def test_sms_gate_refuses_non_https_callback(tmp_path, monkeypatch):
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL', 'http://example.test')
    assert not moses_release_gate.assess(str(tmp_path))['sms']['public_https_origin_configured']
