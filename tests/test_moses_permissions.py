"""Never turn feature-flag presence into direct execution authority."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app.services import moses_permissions


def request(platform='pds', role='office_admin', signed_in=True):
    return SimpleNamespace(
        state=SimpleNamespace(auth_user={'id': 'test-admin'} if signed_in else None,
                              auth_role=role),
        session={'active_platform': platform},
    )


def test_pds_disabled_is_reported_explicitly(monkeypatch):
    for flag in set(moses_permissions.AGENT_FLAGS.values()) | {
        f for rows in moses_permissions.CAPABILITIES.values() for _, _, f in rows if f
    }:
        monkeypatch.delenv(flag, raising=False)
    result = moses_permissions.report(request())
    assert result['workspace'] == 'pds'
    assert result['agent_enabled'] is False
    assert not result['all_configured']
    assert result['all_live_actions_verified'] is False
    assert next(row for row in result['capabilities'] if row['id'] == 'jobs')['status'] == 'read_only'
    assert next(row for row in result['capabilities'] if row['id'] == 'status')['status'] == 'disabled'
    assert 'DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED' in result['missing_configuration_flags']
    assert 'OPENAI_API_KEY' not in str(result)


def test_enabling_flags_only_enables_proposal_not_execution(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'smtp')
    for field in ('DOORKS_SMTP_HOST', 'DOORKS_SMTP_USERNAME', 'DOORKS_SMTP_PASSWORD', 'DOORKS_SMTP_FROM'):
        monkeypatch.setenv(field, 'synthetic-not-real')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_synthetic')
    for platform in ('pds', 'doorks', 'sdc'):
        monkeypatch.setenv(moses_permissions.AGENT_FLAGS[platform], 'true')
        for _, _, flag in moses_permissions.CAPABILITIES[platform]:
            if flag:
                monkeypatch.setenv(flag, 'true')
        result = moses_permissions.report(request(platform))
        assert result['all_configured']
        assert result['agent_enabled']
        assert result['all_live_actions_verified'] is False
        assert all(row['execution_verified'] is False for row in result['capabilities'])
        assert all(row['approval_required'] for row in result['capabilities'] if row['status'] == 'proposal_enabled')
        assert 'TEST MODE ONLY' in result['notes']


@pytest.mark.parametrize('platform,role,signed_in,code', [
    ('pds', 'technician', True, 403),
    ('doorks', 'customer', True, 403),
    ('sdc', 'vendor', True, 403),
    ('invalid', 'office_admin', True, 403),
    ('pds', 'office_admin', False, 401),
])
def test_permissions_cannot_cross_workspace_role_boundary(platform, role, signed_in, code):
    with pytest.raises(HTTPException) as err:
        moses_permissions.report(request(platform, role, signed_in))
    assert err.value.status_code == code


def test_no_secrets_or_workspace_records(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret-not-for-user')
    monkeypatch.setenv('RESEND_API_KEY', 're_secret-not-for-user')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_secret-not-for-user')
    for space in ('pds', 'doorks', 'sdc'):
        raw = str(moses_permissions.report(request(space)))
        assert 'secret-not-for-user' not in raw
        assert 'approval' in raw.lower()


def test_missing_provider_never_claims_ready(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'resend')
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    monkeypatch.setenv('MOSES_ESTIMATE_SEND_ENABLED', 'true')
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED', 'true')
    result = moses_permissions.report(request('doorks'))
    assert 'estimate_email' in result['provider_setup_required']
    assert 'stripe_test' in result['provider_setup_required']
    assert not result['all_configured']
    assert next(item for item in result['capabilities'] if item['id'] == 'estimate_email')['status'] == 'provider_setup_required'
