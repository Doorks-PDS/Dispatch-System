"""Mail identity policy does not send messages or create accounts."""
import pytest
from app.services.moses_mail_identity import identity, general_inquiry_footer


def test_pds_defaults_and_no_implicit_sender(monkeypatch):
    for k in ('MOSES_DOCUMENTS_FROM', 'MOSES_PDS_ESTIMATES_REPLY_TO',
              'MOSES_PDS_INVOICES_REPLY_TO', 'MOSES_PDS_GENERAL_EMAIL'):
        monkeypatch.delenv(k, raising=False)
    estimate = identity('pds', 'estimate')
    invoice = identity('pds', 'invoice')
    assert estimate['from'] == ''
    assert 'sender' in ' '.join(estimate['issues']).lower()
    assert estimate['reply_to'].lower() == 'estimates@prioritydoors.com'
    assert invoice['reply_to'].lower() == 'invoice@prioritydoors.com'
    assert invoice['general_inquiries_email'] == 'reception@prioritydoors.com'
    assert 'reception@prioritydoors.com' in general_inquiry_footer('pds', estimate)


def test_workspace_isolation(monkeypatch):
    monkeypatch.delenv('MOSES_ESTIMATES_REPLY_TO', raising=False)
    assert identity('sdc', 'estimate')['reply_to'] == ''
    assert identity('doorks', 'invoice')['general_inquiries_email'] == ''
    assert general_inquiry_footer('sdc', identity('sdc', 'invoice')) == ''


def test_bad_override_is_not_ignored(monkeypatch):
    monkeypatch.setenv('MOSES_PDS_INVOICES_REPLY_TO', 'not-an-email')
    assert not identity('pds', 'invoice')['reply_to']
    assert identity('pds', 'invoice')['issues']
    monkeypatch.setenv('MOSES_PDS_GENERAL_EMAIL', 'invalid')
    assert not identity('pds', 'estimate')['general_inquiries_email']


def test_override_and_cc(monkeypatch):
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'sending@example.com')
    monkeypatch.setenv('MOSES_PDS_ESTIMATES_REPLY_TO', 'estimates2@prioritydoors.com')
    monkeypatch.setenv('MOSES_PDS_ESTIMATES_CC', 'reception@prioritydoors.com')
    result = identity('pds', 'estimate')
    assert result['from'] == 'sending@example.com'
    assert result['reply_to'] == 'estimates2@prioritydoors.com'
    assert result['cc'] == 'reception@prioritydoors.com'


def test_invalid_categories():
    with pytest.raises(ValueError): identity('other', 'estimate')
    with pytest.raises(ValueError): identity('pds', 'marketing')
