"""Rev78 estimate delivery: no actual SMTP requests (transport is mocked)."""
import json
import pytest
from fastapi import HTTPException
from app.services import moses_estimate_delivery as delivery
from tests.test_moses_estimate_acceptance import setup


def configured(monkeypatch):
    for key, value in {
        'MOSES_ESTIMATE_SEND_ENABLED':'true',
        'MOSES_EMAIL_PROVIDER':'resend',
        'RESEND_API_KEY':'re_synthetic_test_only',
        'MOSES_PUBLIC_BASE_URL':'https://portal.example.com',
        'MOSES_DOCUMENTS_FROM':'documents@example.com',
        'MOSES_ESTIMATES_REPLY_TO':'estimates@example.com',
        'DOORKS_SMTP_HOST':'smtp.example.com',
        'DOORKS_SMTP_USERNAME':'test',
        'DOORKS_SMTP_PASSWORD':'test',
        'DOORKS_SMTP_FROM':'documents@example.com',
    }.items(): monkeypatch.setenv(key, value)


@pytest.mark.parametrize('platform', ['doorks','sdc'])
def test_approved_email_pdf_and_link_sent_once(tmp_path, monkeypatch, platform):
    configured(monkeypatch)
    request, public, folder = setup(tmp_path, platform)
    sent = []
    monkeypatch.setattr(delivery, '_transmit', lambda snapshot, pdf:(sent.append((snapshot, pdf)),'email_mock_estimate')[1])
    proposal = delivery.propose(request, platform, 'estimate-1')['proposal']
    assert proposal['to'] == 'contact@example.com'
    assert not sent
    answer = delivery.decide(request, platform, proposal['id'], True)
    assert answer['state'] == 'sent' and answer['sent']
    assert len(sent) == 1 and sent[0][1].startswith(b'%PDF')
    assert 'https://portal.example.com/doorks-assistant/public/estimates/accept#' in sent[0][0]['text']
    token = sent[0][0]['text'].split('#',1)[1].splitlines()[0]
    from app.services import moses_estimate_acceptance
    assert moses_estimate_acceptance.inspect(public, token)['document_number'] == 'RE00076'
    stored = (folder/'moses_estimate_delivery_actions.json').read_text()
    assert token not in stored and 'portal.example.com/doorks-assistant/public/estimates/accept#' not in stored
    with pytest.raises(HTTPException): delivery.decide(request, platform, proposal['id'], True)
    with pytest.raises(HTTPException): delivery.propose(request, platform, 'estimate-1')


def test_reject_changed_recipient_and_uncertain(tmp_path, monkeypatch):
    configured(monkeypatch)
    req, _, folder = setup(tmp_path)
    p = delivery.propose(req, 'doorks', 'estimate-1')['proposal']
    assert delivery.decide(req, 'doorks', p['id'], False)['state'] == 'rejected'
    p = delivery.propose(req, 'doorks', 'estimate-1')['proposal']
    file = folder/'estimates_invoices.json'
    data = json.loads(file.read_text())
    data[0]['contact_email'] = 'other@example.com'
    file.write_text(json.dumps(data))
    with pytest.raises(HTTPException) as err: delivery.decide(req, 'doorks', p['id'], True)
    assert err.value.status_code == 409
    p = delivery.propose(req, 'doorks', 'estimate-1')['proposal']
    monkeypatch.setattr(delivery, '_transmit', lambda *args: (_ for _ in ()).throw(TimeoutError()))
    result = delivery.decide(req, 'doorks', p['id'], True)
    assert result['state'] == 'uncertain'
    with pytest.raises(HTTPException): delivery.propose(req, 'doorks', 'estimate-1')
    with pytest.raises(HTTPException): delivery.decide(req, 'doorks', p['id'], True)


def test_disabled_wrong_workspace_and_invalid_origin(tmp_path, monkeypatch):
    configured(monkeypatch)
    req, _, _ = setup(tmp_path)
    req.session['active_platform'] = 'sdc'
    with pytest.raises(HTTPException) as err: delivery.propose(req, 'doorks', 'estimate-1')
    assert err.value.status_code == 403
    req.session['active_platform'] = 'doorks'
    monkeypatch.delenv('MOSES_ESTIMATE_SEND_ENABLED')
    with pytest.raises(HTTPException) as err: delivery.propose(req, 'doorks', 'estimate-1')
    assert err.value.status_code == 503
    monkeypatch.setenv('MOSES_ESTIMATE_SEND_ENABLED', 'true')
    monkeypatch.setenv('MOSES_PUBLIC_BASE_URL', 'http://portal.example.com')
    with pytest.raises(HTTPException) as err: delivery.propose(req, 'doorks', 'estimate-1')
    assert err.value.status_code == 503


def test_preexisting_link_blocks_email(tmp_path, monkeypatch):
    configured(monkeypatch)
    req, _, _ = setup(tmp_path)
    from app.services import moses_estimate_acceptance as acceptance
    acceptance.issue(req, 'doorks', 'estimate-1')
    p = delivery.propose(req, 'doorks', 'estimate-1')['proposal']
    with pytest.raises(HTTPException) as err: delivery.decide(req, 'doorks', p['id'], True)
    assert err.value.status_code == 409
    assert delivery.history(req, 'doorks', 'estimate-1')[0]['state'] == 'pending'


def test_agent_estimate_email_proposal_tool_is_non_sending(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.services import moses_agent
    configured(monkeypatch)
    req, _, folder = setup(tmp_path, 'doorks')
    captured = {}
    sent = []
    monkeypatch.setattr(delivery, '_transmit', lambda *args: sent.append(args))
    class FakeAgent:
        def __init__(self, **kwargs): captured.update(kwargs)
    class FakeRunner:
        @staticmethod
        def run_sync(agent, turns, **kwargs):
            tool = next(t for t in captured['tools'] if t.__name__ == 'propose_customer_estimate_email')
            data = json.loads(tool('estimate-1'))
            assert data['proposal']['to'] == 'contact@example.com'
            assert data['proposal']['state'] == 'pending'
            return SimpleNamespace(final_output='Approval request prepared; no email sent')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(Agent=FakeAgent, Runner=FakeRunner,
                        RunConfig=lambda **kwargs: None, function_tool=lambda fn: fn))
    assert 'no email sent' in moses_agent.answer(req, 'Prepare estimate email', [])
    assert not sent
    assert delivery.history(req, 'doorks', 'estimate-1')[0]['state'] == 'pending'
    req.session['active_platform'] = 'pds'
    with pytest.raises(HTTPException) as exc:
        delivery.propose(req, 'doorks', 'estimate-1')
    assert exc.value.status_code == 403
