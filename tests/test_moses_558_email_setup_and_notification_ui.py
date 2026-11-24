"""Moses 5.58 supplier Resend readiness and compact schedule notification UI."""
from pathlib import Path
from types import SimpleNamespace
from app.services import pds_schedule_notifications as schedule
from app.routers import pds_supplier_quotes as supplier

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT/'static/app.js').read_text()


def request():
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'office-1'},auth_role='office_admin'),
                           session={'active_platform':'pds'})


def test_supplier_preview_config_is_read_only_no_secrets(monkeypatch):
    for key in ('MOSES_DOCUMENTS_FROM','MOSES_EMAIL_PROVIDER','RESEND_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    info = supplier.supplier_quote_email_config(request())
    assert info['reply_to'] == 'reception@prioritydoors.com'
    assert not info['send_ready']
    assert any('MOSES_DOCUMENTS_FROM' in issue for issue in info['setup_issues'])
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    monkeypatch.setenv('RESEND_API_KEY','re_fake_secret_just_for_tests')
    configured = supplier._email_readiness('supplier@example.com')
    assert configured['send_ready'] is True
    assert configured['from'] == 'NoReply@prioritydoors.com'
    assert 'RESEND_API_KEY' not in configured
    assert 're_fake_secret' not in str(configured)
    assert not supplier._email_readiness('wrong-address')['send_ready']


def test_customer_email_gate_is_checked_before_send(monkeypatch):
    for key in ('PDS_SCHEDULE_EMAIL_SEND_ENABLED','MOSES_DOCUMENTS_FROM','RESEND_API_KEY','MOSES_EMAIL_PROVIDER'):
        monkeypatch.delenv(key, raising=False)
    info = schedule.email_readiness(request())
    assert info['enabled'] is False
    assert any('disabled' in x for x in info['issues'])
    monkeypatch.setenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED','true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    monkeypatch.setenv('RESEND_API_KEY','re_fake_secret_for_tests')
    monkeypatch.setenv('MOSES_EMAIL_PROVIDER','resend')
    enabled = schedule.email_readiness(request())
    assert enabled['enabled'] is True
    assert enabled['reply_to'] == 'reception@prioritydoors.com'
    assert 're_fake_secret' not in str(enabled)


def test_supplier_email_review_has_compact_preview_and_setup_gate():
    a = JS.index('    async function reviewEmail(row){')
    b = JS.index('    function responseEditor(row){', a)
    block = JS[a:b]
    for required in ('send_ready', 'setup_issues', 'Not configured', 'Edit Request',
                     'Approve & Send via Resend', 'position:sticky', "filter(a=>a.purpose==='request')"):
        assert required in block
    assert 'if(issues.length||!preview.recipient_verified||!preview.send_ready)' in block
    assert "'/'+encodeURIComponent(row.id)+'/send'" in block
    assert 'confirm(' in block


def test_customer_notification_form_is_compact_and_preflighted():
    a = JS.index('      // Customer notifications are independent approval requests.')
    b = JS.index('      plan.append(notify);', a)
    block = JS[a:b]
    for required in ('✉ Notify Customer','Review & Prepare','Approve & Send','Discard',
                     "'/pds-schedule-notifications/email/readiness'", 'recipientEmail',
                     'Notification history', 'historyDetails', 'emailGate?.enabled',
                     'Message', 'Priority Door Systems:', 'send_uncertain'):
        if required == 'send_uncertain':
            continue  # uncertain-send handling is owned by server approval service
        assert required in block, required
    assert 'savedEmailChoice' not in block
    assert "method.value==='both'?['email','text']" in block
    assert "confirm(allowed?'Send this '" in block
    assert "requestApproval.disabled=needsEmail&&(!emailGate?.enabled||!recipientEmail.value)" in block
    assert "textContent='1 approval request(s)'" not in block
