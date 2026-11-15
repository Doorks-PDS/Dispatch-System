"""Rev82: invoice email is approved, test-only, AP-routed, duplicate guarded."""
import json
import pytest
from fastapi import HTTPException
from app.services import moses_invoice_delivery as mail
from app.services import moses_stripe as stripe
from tests.test_moses_stripe import setup as stripe_setup, mock_session


def setup(tmp_path, monkeypatch, platform='doorks'):
    request = stripe_setup(tmp_path, monkeypatch, platform)
    monkeypatch.setenv('MOSES_INVOICE_SEND_ENABLED', 'true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM', 'documents@example.com')
    monkeypatch.setenv('MOSES_INVOICES_REPLY_TO', 'invoices@example.com')
    monkeypatch.setenv('DOORKS_SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('DOORKS_SMTP_USERNAME', 'test')
    monkeypatch.setenv('DOORKS_SMTP_PASSWORD', 'test')
    monkeypatch.setenv('DOORKS_SMTP_FROM', 'documents@example.com')
    directory = tmp_path/'business_workspaces'/platform
    path = directory/'estimates_invoices.json'
    data = json.loads(path.read_text())
    data[0].update(customer='Example', line_items=[{'description':'Door repair','quantity':1,'rate':'125.50'}],
                   tax_rate=0, tax_amount=0)
    path.write_text(json.dumps(data))
    mock_session(monkeypatch)
    checkout = stripe.propose(request, platform, 'inv1')['proposal']
    assert stripe.decide(request, platform, checkout['id'], True)['state'] == 'checkout_ready'
    return request, path


@pytest.mark.parametrize('platform', ['doorks', 'sdc'])
def test_email_approval_pdf_and_ap_address(tmp_path, monkeypatch, platform):
    request, path = setup(tmp_path, monkeypatch, platform)
    delivered = []
    monkeypatch.setattr(mail, '_transmit', lambda snap, pdf: delivered.append((snap, pdf)))
    proposal = mail.propose(request, platform, 'inv1')['proposal']
    assert proposal['to'] == 'ap@example.com' and proposal['recipient_source'] == 'customer_ap'
    assert not delivered
    response = mail.decide(request, platform, proposal['id'], True)
    assert response['sent'] and len(delivered) == 1
    assert delivered[0][1].startswith(b'%PDF')
    assert 'checkout.stripe.com' in delivered[0][0]['text']
    log = (path.parent/'moses_invoice_delivery_actions.json').read_text()
    assert 'checkout.stripe.com' not in log
    with pytest.raises(HTTPException): mail.decide(request, platform, proposal['id'], True)
    with pytest.raises(HTTPException): mail.propose(request, platform, 'inv1')


def test_rejection_stale_amount_and_uncertain_delivery(tmp_path, monkeypatch):
    req, path = setup(tmp_path, monkeypatch)
    p = mail.propose(req, 'doorks', 'inv1')['proposal']
    assert mail.decide(req, 'doorks', p['id'], False)['state'] == 'rejected'
    p = mail.propose(req, 'doorks', 'inv1')['proposal']
    data = json.loads(path.read_text()); data[0]['total'] = '130.50'; path.write_text(json.dumps(data))
    with pytest.raises(HTTPException): mail.decide(req, 'doorks', p['id'], True)
    data[0]['total'] = '125.50'; path.write_text(json.dumps(data))
    p = mail.propose(req, 'doorks', 'inv1')['proposal']
    monkeypatch.setattr(mail, '_transmit', lambda *args: (_ for _ in ()).throw(TimeoutError()))
    assert mail.decide(req, 'doorks', p['id'], True)['state'] == 'uncertain'
    with pytest.raises(HTTPException): mail.propose(req, 'doorks', 'inv1')


def test_paid_disabled_and_isolated(tmp_path, monkeypatch):
    req, _ = setup(tmp_path, monkeypatch)
    req.session['active_platform'] = 'sdc'
    with pytest.raises(HTTPException) as exc: mail.propose(req, 'doorks', 'inv1')
    assert exc.value.status_code == 403
    req.session['active_platform'] = 'doorks'
    monkeypatch.delenv('MOSES_INVOICE_SEND_ENABLED')
    with pytest.raises(HTTPException) as exc: mail.propose(req, 'doorks', 'inv1')
    assert exc.value.status_code == 503
    monkeypatch.setenv('MOSES_INVOICE_SEND_ENABLED', 'true')
    # A paid checkout is no longer an active link and may not be emailed.
    path = req.app.state.data_dir/'business_workspaces'/'doorks'/'moses_stripe_checkout.json'
    rows = json.loads(path.read_text()); rows[0]['state'] = 'paid'; path.write_text(json.dumps(rows))
    with pytest.raises(HTTPException) as exc: mail.propose(req, 'doorks', 'inv1')
    assert exc.value.status_code == 409

@pytest.mark.parametrize('platform', ['doorks', 'sdc'])
def test_moses_invoice_email_tool_only_prepares_request(tmp_path, monkeypatch, platform):
    import sys
    from types import SimpleNamespace
    from app.services import moses_agent
    request, _ = setup(tmp_path, monkeypatch, platform)
    captured = {}
    delivered = []
    monkeypatch.setattr(mail, '_transmit', lambda *args: delivered.append(args))

    class FakeAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            names = {tool.__name__ for tool in captured['tools']}
            assert 'propose_customer_invoice_email' in names
            assert 'send_customer_invoice_email' not in names
            tool = next(tool for tool in captured['tools'] if tool.__name__ == 'propose_customer_invoice_email')
            proposal = json.loads(tool('inv1'))['proposal']
            assert proposal['state'] == 'pending'
            assert proposal['to'] == 'ap@example.com'
            assert proposal['attachment_filename'].endswith('.pdf')
            return SimpleNamespace(final_output='Invoice email prepared for approval; not sent')

    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=FakeAgent, Runner=FakeRunner, RunConfig=lambda **kwargs: None,
        function_tool=lambda fn: fn))
    assert 'not sent' in moses_agent.answer(request, 'Prepare invoice email', [])
    assert not delivered
    assert mail.history(request, platform, 'inv1')[0]['state'] == 'pending'


def test_pds_agent_does_not_have_invoice_mail_tool(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.services import moses_agent
    from tests.test_moses_doorks_actions import req
    captured = {}
    class FakeAgent:
        def __init__(self, **kwargs): captured.update(kwargs)
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            return SimpleNamespace(final_output='PDS invoice delivery is not configured.')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=FakeAgent, Runner=FakeRunner, RunConfig=lambda **kwargs: None,
        function_tool=lambda fn: fn))
    moses_agent.answer(req(tmp_path, platform='pds'), 'Send invoice', [])
    assert 'propose_customer_invoice_email' not in {t.__name__ for t in captured['tools']}
