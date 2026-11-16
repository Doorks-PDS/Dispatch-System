"""All Moses workspaces share one Resend sender. Network calls are mocked."""
import pytest
from fastapi import HTTPException
from app.services import moses_email_transport as mail
from app.services.moses_mail_identity import identity


def test_one_resend_sender_for_pds_doorks_sdc(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('RESEND_API_KEY','re_test_fake_not_a_live_key')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setenv('MOSES_PDS_FROM','wrong@notused.example')
    for workspace in ('pds','doorks','sdc'):
        assert identity(workspace,'estimate')['from']=='NoReply@prioritydoors.com'
    assert identity('pds','estimate')['reply_to'].casefold()=='estimates@prioritydoors.com'
    assert identity('pds','invoice')['reply_to'].casefold()=='invoice@prioritydoors.com'
    mail.ready('NoReply@prioritydoors.com')
    with pytest.raises(HTTPException):mail.ready('wrong@notused.example')


def test_outlook_smtp_fails_closed_even_with_credentials(monkeypatch):
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    for k in ('DOORKS_SMTP_HOST','DOORKS_SMTP_USERNAME','DOORKS_SMTP_PASSWORD','DOORKS_SMTP_FROM'):
        monkeypatch.setenv(k,'legacy-configured')
    for provider in ('smtp','', 'outlook'):
        monkeypatch.setenv('MOSES_EMAIL_PROVIDER',provider)
        with pytest.raises(HTTPException) as error:mail.provider()
        assert error.value.status_code==503


def test_resend_missing_api_key_fails_closed(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.delenv('RESEND_API_KEY',raising=False)
    with pytest.raises(HTTPException):mail.ready('NoReply@prioritydoors.com')
