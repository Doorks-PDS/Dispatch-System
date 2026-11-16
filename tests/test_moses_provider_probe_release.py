"""Read-only Resend / Stripe provider connectivity regressions; no HTTP network calls."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_provider_probe as probe


def request(platform='pds', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'test'}, auth_role=role),
                           session={'active_platform': platform})


def set_config(monkeypatch):
    monkeypatch.setenv('MOSES_PDS_FROM', 'ignored@example.com')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'NoReply@prioritydoors.com')
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER', 'resend')
    monkeypatch.setenv('RESEND_API_KEY', 're_sample')
    monkeypatch.setenv('MOSES_STRIPE_TEST_ENABLED', 'true')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_dummy')
    monkeypatch.setenv('MOSES_STRIPE_EXPECTED_ACCOUNT_ID', 'acct_expected')


def test_both_providers_read_only_and_correct_sender(monkeypatch):
    set_config(monkeypatch)
    calls=[]
    def read(url,key,**kwargs):
        calls.append((url,key))
        if 'resend' in url: return {'data': [{'name':'prioritydoors.com','status':'verified'}]}
        return {'id':'acct_expected','object':'account'}
    monkeypatch.setattr(probe,'_json_get',read)
    outcome=probe.inspect(request())
    assert outcome['resend']['sender_domain_verified']
    assert outcome['stripe']['expected_account_matched']
    assert not outcome['customer_email_sent'] and not outcome['checkout_created']
    assert all(url.startswith('https://') for url,key in calls)
    assert all('sample' not in json.dumps(outcome) for _ in [None])
    assert len(calls)==2


def test_unverified_sender_not_reported_ready(monkeypatch):
    set_config(monkeypatch)
    monkeypatch.setattr(probe,'_json_get',lambda url,key,**kw:
                        {'data':[{'name':'another.com','status':'verified'}]} if 'resend' in url else {'id':'acct_expected','object':'account'})
    assert not probe.inspect(request())['resend']['sender_domain_verified']


def test_wrong_stripe_account_fails_closed(monkeypatch):
    set_config(monkeypatch)
    monkeypatch.setattr(probe,'_json_get',lambda url,key,**kw:
                        {'data':[]} if 'resend' in url else {'id':'acct_other','object':'account'})
    r=probe.inspect(request());assert not r['stripe']['expected_account_matched']
    assert r['stripe']['result']=='sandbox_account_mismatch'


def test_missing_credentials_are_not_verified(monkeypatch):
    for k in ('MOSES_EMAIL_PROVIDER','RESEND_API_KEY','MOSES_STRIPE_TEST_ENABLED','STRIPE_SECRET_KEY'):
        monkeypatch.delenv(k,raising=False)
    monkeypatch.setattr(probe,'_json_get',lambda *a,**k: pytest.fail('external HTTP attempted'))
    r=probe.inspect(request());assert not r['stripe']['test_key_configured']
    assert not r['resend']['sender_domain_verified']


def test_no_secrets_in_failing_provider_response(monkeypatch):
    set_config(monkeypatch)
    def fail(*a,**kw): raise ValueError('sk_test_do_not_expose')
    monkeypatch.setattr(probe,'_json_get',fail)
    output=json.dumps(probe.inspect(request()))
    assert 'sk_test_do_not_expose' not in output
    assert 'provider_check_failed' in output


def test_active_office_admin_required(monkeypatch):
    set_config(monkeypatch)
    monkeypatch.setattr(probe,'_json_get',lambda *a,**kw: pytest.fail('external HTTP attempted'))
    with pytest.raises(HTTPException) as e: probe.inspect(request('pds','technician'))
    assert e.value.status_code==403
    with pytest.raises(HTTPException): probe.inspect(request('invalid'))


def test_pds_and_atlas_share_one_sender(monkeypatch):
    set_config(monkeypatch)
    from app.services.moses_mail_identity import identity
    assert identity('pds','estimate')['from'].casefold() == 'noreply@prioritydoors.com'
    assert identity('sdc','estimate')['from'].casefold() == 'noreply@prioritydoors.com'
    assert identity('doorks','estimate')['from'].casefold() == 'noreply@prioritydoors.com'
