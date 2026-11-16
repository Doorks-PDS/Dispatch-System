"""Provider receipt mapping for all four approved send paths (no network)."""
import pytest
from app.services import moses_email_transport as transport

def test_resend_receipt_is_acceptance_not_delivered(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    receipt=transport.delivery_receipt('email_123-mock')
    assert receipt == {'transport':'resend','provider_message_id':'email_123-mock',
                       'delivery_status':'accepted_by_provider'}
    assert 'delivered' not in str(receipt)

@pytest.mark.parametrize('bad',[None,'',42,'bad/id','bad\nheader','x'*257])
def test_reject_unverifiable_receipts(monkeypatch,bad):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    with pytest.raises(RuntimeError):transport.delivery_receipt(bad)

def test_outlook_smtp_not_accepted_as_moses_provider(monkeypatch):
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','smtp')
    from fastapi import HTTPException
    with pytest.raises(HTTPException):transport.delivery_receipt(None)
