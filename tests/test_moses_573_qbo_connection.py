"""QuickBooks 5.73 readiness: OAuth authorization and read-only verification only.

All tests mock the Intuit endpoints; no provider calls or accounting writes occur.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.services import pds_qbo_connection as connection


def req(tmp_path, role='office_admin'):
    return SimpleNamespace(
        state=SimpleNamespace(auth_role=role, auth_user={'id':'admin-1','username':'admin'}),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, project_root=tmp_path.parent/'source')),
    )


def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('PDS_QUICKBOOKS_EDITION', 'online')
    monkeypatch.setenv('PDS_QBO_ENVIRONMENT', 'sandbox')
    monkeypatch.setenv('PDS_QBO_CLIENT_ID', 'test-intuit-client-id')
    monkeypatch.setenv('PDS_QBO_CLIENT_SECRET', 'test-intuit-secret')
    monkeypatch.setenv('PDS_QBO_REDIRECT_URI', 'https://demo.example.com/pds-quickbooks/oauth/callback')
    monkeypatch.setenv('PDS_QBO_TOKEN_ENCRYPTION_KEY', Fernet.generate_key().decode())
    monkeypatch.setenv('DOORKS_SESSION_SECRET', 'a-random-example-session-secret-123456789')
    monkeypatch.delenv('RENDER',raising=False)


def test_no_connection_or_provider_write_before_user_authorizes(tmp_path, monkeypatch):
    setup(tmp_path,monkeypatch)
    r=req(tmp_path)
    state=connection.configuration(r)
    assert state['configured'] is True
    assert state['authorized'] is False
    assert state['posting_enabled'] is False
    assert not (tmp_path/connection.CONNECTED_FILE).exists()
    start=connection.authorization_url(r)
    assert start['authorization_url'].startswith('https://appcenter.intuit.com/connect/oauth2?')
    assert 'sandbox'==start['environment'] and start['writes_accounting_transactions'] is False
    assert not (tmp_path/connection.CONNECTED_FILE).exists()


def test_callback_token_is_encrypted_and_company_verification_readonly(tmp_path, monkeypatch):
    setup(tmp_path,monkeypatch)
    r=req(tmp_path)
    connection.authorization_url(r)
    state=r.session[connection.SESSION_KEY]['state']
    monkeypatch.setattr(connection,'_token_exchange',lambda form:{
        'access_token':'secret-fake-test-access','refresh_token':'secret-fake-test-refresh','expires_in':3600})
    result=connection.finish_authorization(r,code='valid-code-123456',state=state,realm_id='12345')
    assert result['authorized'] and result['company_id']=='12345'
    raw=(tmp_path/connection.CONNECTED_FILE).read_bytes()
    assert b'secret-fake-test-refresh' not in raw
    assert b'secret-fake-test-access' not in raw
    calls=[]
    class FakeRead:
        def read(self, maximum):return json.dumps({'CompanyInfo':{'Id':'12345','CompanyName':'PDS Sandbox'}}).encode()
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def fake_open(request,timeout):
        calls.append((request.full_url,request.get_method()))
        return FakeRead()
    monkeypatch.setattr(connection,'urlopen',fake_open)
    checked=connection.verify_company(r)
    assert checked['company_name']=='PDS Sandbox'
    assert calls==[('https://sandbox-quickbooks.api.intuit.com/v3/company/12345/companyinfo/12345','GET')]
    flags=connection.configuration(r)
    assert flags['authorized'] and flags['last_read_only_verification']
    assert flags['posting_enabled'] is False


def test_csrf_or_role_failure_does_not_store_tokens(tmp_path, monkeypatch):
    setup(tmp_path,monkeypatch)
    r=req(tmp_path)
    connection.authorization_url(r)
    with pytest.raises(HTTPException) as err:
        connection.finish_authorization(r,code='valid-code-123456',state='wrong-state',realm_id='12345')
    assert err.value.status_code==403
    assert not (tmp_path/connection.CONNECTED_FILE).exists()
    restricted=req(tmp_path,role='lead')
    for op in (lambda:connection.configuration(restricted),lambda:connection.authorization_url(restricted)):
        with pytest.raises(HTTPException) as e:op()
        assert e.value.status_code==403
