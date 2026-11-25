"""Cumulative rev 5.67: verified invoice handoff + Moses readiness, no external writes."""
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.routers import pds_quickbooks_bridge as route


def setup_request(tmp_path, role='office_admin'):
    docs_dir = tmp_path / 'documents'; docs_dir.mkdir()
    (docs_dir / 'JS00021.pdf').write_bytes(b'%PDF-1.5\nexample\n')
    invoice = {'type': 'invoice', 'number': 'JS00021', 'filename': 'JS00021.pdf',
        'job_id': 'abc', 'job_number': '1126-21', 'customer': 'Test PDS Customer',
        'tax_rate': 7.75, 'items': [
            {'qty': 2, 'rate': 100, 'taxable': False}, {'qty': 1, 'rate': 40, 'taxable': True}],
        'date': '2026-11-24', 'terms': 'Net 30'}
    docs = SimpleNamespace(dir=docs_dir, list_documents=lambda: [invoice])
    jobs = SimpleNamespace(list_jobs=lambda: [{'id': 'abc', 'job_number': '1126-21', 'customer': invoice['customer']}])
    req = SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'admin'},auth_role=role),
        session={'active_platform':'pds'}, app=SimpleNamespace(state=SimpleNamespace(
            documents_store=docs, calendar_store=jobs, data_dir=str(tmp_path))))
    return req, invoice


def mark_sent(req):
    p = Path(req.app.state.data_dir) / 'moses_pds_document_delivery_actions.json'
    p.write_text(json.dumps([{'snapshot': {'kind': 'invoice', 'number': 'JS00021',
        'job_id': 'abc', 'job_number': '1126-21',
        'pdf_sha256': hashlib.sha256((Path(req.app.state.data_dir) / 'documents/JS00021.pdf').read_bytes()).hexdigest()},
        'state': 'sent'}]))


def test_ready_requires_real_job_and_send(tmp_path):
    req, doc=setup_request(tmp_path)
    assert qb.preview(req)['invoices'][0]['ready'] is False
    mark_sent(req)
    row = qb.preview(req)['invoices'][0]
    assert row['ready'] is True
    assert row['total'] == '243.10'
    assert row['tax'] == '3.10'
    doc['job_number'] = 'WRONG'
    assert not qb.preview(req)['invoices'][0]['ready']


def test_stage_idempotent_and_never_claim_sync(tmp_path):
    req, doc=setup_request(tmp_path)
    mark_sent(req)
    row=qb.preview(req)['invoices'][0]
    created=qb.prepare(req,row['number'],row['fingerprint'])
    assert created['state']=='prepared_for_review' and created['pushed_to_quickbooks'] is False
    assert qb.prepare(req,row['number'],row['fingerprint'])['duplicate']
    assert 'JS00021' in qb.export_review_csv(req)
    doc['items'][0]['rate']=123
    changed=qb.preview(req)['invoices'][0]
    with pytest.raises(HTTPException) as exc:
        qb.prepare(req,changed['number'],changed['fingerprint'])
    assert exc.value.status_code==409


def test_access_and_confirmation_required(tmp_path):
    req, _=setup_request(tmp_path,'tech')
    with pytest.raises(HTTPException) as exc:qb.preview(req)
    assert exc.value.status_code==403
    req.state.auth_role='office'
    with pytest.raises(HTTPException) as exc:qb.preview(req)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:qb.status(req)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:qb.prepare(req,'JS00021','0'*64)
    assert exc.value.status_code==403
    req.state.auth_role='office_admin'
    with pytest.raises(HTTPException) as exc:route.prepare_invoice(
        route.PrepareRequest(invoice_number='JS00021',fingerprint='0'*64),req)
    assert exc.value.status_code==422
    req.session['active_platform']='sdc'
    with pytest.raises(HTTPException) as exc:qb.status(req)
    assert exc.value.status_code==403


def test_no_spreadsheet_formula_in_customer_name(tmp_path):
    req,doc=setup_request(tmp_path)
    doc['customer']='=HYPERLINK("a")'
    mark_sent(req)
    row=qb.preview(req)['invoices'][0]
    qb.prepare(req,row['number'],row['fingerprint'])
    assert "'=HYPERLINK" in qb.export_review_csv(req)


def test_moses_readiness_exposes_missing_setup_without_keys(monkeypatch):
    from app.services.moses_agent import readiness
    for name in ('OPENAI_API_KEY','DOORKS_MOSES_PDS_AGENT_ENABLED','DOORKS_MOSES_WEB_SEARCH_ENABLED'):
        monkeypatch.delenv(name,raising=False)
    state=readiness('pds')
    assert not state['internet_research_verified']
    assert not state['live_api_verified']
    assert 'OPENAI_API_KEY' in state['missing_setup']
    monkeypatch.setenv('OPENAI_API_KEY','test-not-real')
    monkeypatch.setenv('DOORKS_MOSES_PDS_AGENT_ENABLED','true')
    monkeypatch.setenv('DOORKS_MOSES_WEB_SEARCH_ENABLED','true')
    ready=readiness('pds')
    assert 'OPENAI_API_KEY' not in ready['missing_setup']
    assert ready['internet_research_verified'] is False


def test_integration_health_is_admin_only_and_no_secret_values(tmp_path, monkeypatch):
    from app.routers import doorks_assistant as assistant
    req, _=setup_request(tmp_path)
    monkeypatch.setenv('RESEND_WEBHOOK_SECRET', 'whsec_fake_never_real')
    response=assistant.integration_health(req)
    assert response['resend_delivery_webhook_configured'] is True
    assert response['delivery_guaranteed'] is False
    assert 'whsec_fake_never_real' not in str(response)
    req.state.auth_role='office'
    with pytest.raises(HTTPException) as exc:assistant.integration_health(req)
    assert exc.value.status_code==403


def test_public_web_probe_classifies_errors_without_provider_payload(monkeypatch):
    import sys
    from app.services import moses_agent, moses_web_probe
    monkeypatch.setattr(moses_agent, 'readiness', lambda workspace: {
        'ready_for_live_check': True, 'internet_research_requested': True,
        'web_live_test_enabled': True})
    class AuthenticationError(Exception): pass
    class Agent:
        def __init__(self, **kwargs): pass
    class WebSearchTool:
        def __init__(self, **kwargs): pass
    class RunConfig:
        def __init__(self, **kwargs): pass
    class Runner:
        @staticmethod
        def run_sync(*args, **kwargs): raise AuthenticationError('secret API credential text')
    monkeypatch.setitem(sys.modules, 'agents', SimpleNamespace(
        Agent=Agent, WebSearchTool=WebSearchTool, RunConfig=RunConfig, Runner=Runner))
    result=moses_web_probe.check('pds')
    assert result['result']=='api_key_rejected'
    assert result['web_search_verified'] is False
    assert 'secret' not in str(result)


def test_changed_pdf_not_counted_as_sent(tmp_path):
    req, _=setup_request(tmp_path)
    mark_sent(req)
    assert qb.preview(req)['invoices'][0]['ready']
    pdf=Path(req.app.state.documents_store.dir) / 'JS00021.pdf'
    pdf.write_bytes(b'%PDF-1.6\nchanged copy')
    revised=qb.preview(req)['invoices'][0]
    assert revised['ready'] is False
    assert 'Current PDF not confirmed accepted by Resend' in revised['needs_review']
