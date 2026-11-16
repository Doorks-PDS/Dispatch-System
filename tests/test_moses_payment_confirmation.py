"""Rev84: cross-step test with mocked provider/SMTP, not real external execution."""
import json
import pytest
from fastapi import HTTPException
from app.services import moses_stripe as stripe
from app.services import moses_invoice_delivery as mail
from app.services import moses_payment_confirmation as confirm
from tests.test_moses_invoice_delivery import setup as invoice_setup
from tests.test_moses_stripe import signed, event


@pytest.mark.parametrize('platform', ['doorks', 'sdc'])
def test_complete_checkout_email_webhook_receipt_preview(tmp_path, monkeypatch, platform):
    req, invoice_path = invoice_setup(tmp_path, monkeypatch, platform)
    outbound = []
    monkeypatch.setattr(mail, '_transmit', lambda msg, pdf:(outbound.append((msg, pdf)),'email_mock_payment')[1])
    proposal = mail.propose(req, platform, 'inv1')['proposal']
    assert not outbound
    assert mail.decide(req, platform, proposal['id'], True)['sent']
    assert len(outbound) == 1 and outbound[0][1].startswith(b'%PDF')
    checkout_id = stripe.history(req, platform, 'inv1')[0]['id']
    with pytest.raises(HTTPException): confirm.preview(req, platform, 'inv1')
    body, sig = signed(event(checkout_id))
    assert stripe.webhook(req, body, sig)['processed']
    assert stripe.webhook(req, body, sig)['duplicate']
    result = confirm.preview(req, platform, 'inv1')
    assert result['to'] == 'ap@example.com'
    assert result['stripe_payment_confirmed'] and not result['accounting_reconciled']
    assert not result['send_enabled'] and 'confirmation' in result['subject'].lower()
    assert 'checkout.stripe.com' not in json.dumps(result)
    assert json.loads(invoice_path.read_text())[0]['status'] == 'Sent'


def test_preview_denies_other_platform_and_changed_invoice(tmp_path, monkeypatch):
    req, invoice_path = invoice_setup(tmp_path, monkeypatch)
    checkout_id = stripe.history(req, 'doorks', 'inv1')[0]['id']
    body, sig = signed(event(checkout_id))
    assert stripe.webhook(req, body, sig)['processed']
    req.session['active_platform'] = 'sdc'
    with pytest.raises(HTTPException): confirm.preview(req, 'doorks', 'inv1')
    req.session['active_platform'] = 'doorks'
    data = json.loads(invoice_path.read_text())
    data[0]['total'] = '225.50'
    invoice_path.write_text(json.dumps(data))
    with pytest.raises(HTTPException) as exc:
        confirm.preview(req, 'doorks', 'inv1')
    assert exc.value.status_code == 409


def test_legacy_and_moses_webhooks_are_separate():
    from main import app
    paths = {r.path for r in app.routes}
    assert '/doorks-portals/stripe/webhook' in paths
    assert '/doorks-assistant/public/stripe/webhook' in paths
    from app.routers.doorks_assistant import stripe_webhook_routing
    # The route requires a signed-in administrator; no public routing disclosure.
    from types import SimpleNamespace
    fake = SimpleNamespace(state=SimpleNamespace(auth_user={'id':'a'}, auth_role='office_admin'),
                           session={'active_platform':'doorks'})
    data = stripe_webhook_routing(fake)
    assert data['separate_ledgers'] is True
    assert data['legacy_portal'] != data['moses_test']
