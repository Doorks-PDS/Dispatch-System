"""No external accounts, credentials, or provider transaction writes are used."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import os
import re
import subprocess

import pytest
from fastapi import HTTPException
from app.services import pds_qbo_connection as connection
from app.services import pds_qbo_trial_plan as trial

ROOT = Path(__file__).resolve().parents[1]


def test_completion_action_rules_and_saved_source_handoff():
    js = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    match = re.search(r'  function pdsCompletionDocumentActions\(status, isRecommendation = false\) \{.*?\n  \}', js, re.S)
    assert match is not None
    program = match.group(0) + '\nconsole.log(JSON.stringify([' + ','.join(
        f"pdsCompletionDocumentActions({status!r}, {recommendation})"
        for status, recommendation in (
            ('Dispatch', 'false'), ('Scheduled', 'false'), ('Quote', 'false'),
            ('Parts on Order', 'false'), ('Complete/Quote', 'false'),
            ('Complete', 'false'), ('Complete', 'true'), ('complete / quote', 'false'),
        )
    ) + ']));'
    output = subprocess.check_output(['node', '-e', program], text=True)
    import json
    result = json.loads(output)
    assert result == [
        ['estimate'], ['estimate'], ['estimate'], ['estimate'],
        ['estimate', 'invoice'], ['invoice'], ['estimate'], ['estimate', 'invoice']
    ]
    assert 'Save & Invoice' in js
    assert "btnSaveAndInvoice.addEventListener('click'" in js
    assert "sourceFormId:String(savedForm.id)" in js
    assert "String(selected.id||'')!==String(ctx.sourceFormId)" in js
    assert "invoiceSourceEstimate:linkedEstimate||null" in js
    assert "btnSaveAndInvoice.disabled = true" in js


def test_render_source_subdirectory_needs_real_mount(monkeypatch, tmp_path):
    # Existing Render disk /opt/render/project/src/data is legitimately mounted
    # inside source_root. Ordinary source subdirectories must still fail closed.
    source = tmp_path / 'src'
    disk = source / 'data'
    disk.mkdir(parents=True)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=disk, project_root=source)))
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.setenv('PDS_QBO_ENVIRONMENT', 'sandbox')
    monkeypatch.setattr(os.path, 'ismount', lambda p: Path(p) == disk)
    assert connection._durable_path(request) == disk / connection.CONNECTED_FILE
    monkeypatch.setattr(os.path, 'ismount', lambda p: False)
    with pytest.raises(HTTPException) as exc:
        connection._durable_path(request)
    assert exc.value.status_code == 503
    request.app.state.data_dir = source
    with pytest.raises(HTTPException):
        connection._durable_path(request)


def test_trial_report_never_posts_and_requires_review(monkeypatch):
    doc = {'kind': 'invoice', 'pds_number': 'JS00044', 'lines': [{'position':1}],
           'source_fingerprint': 'a'*64, 'total': '100.00', 'terms':'NET30', 'currency':'USD'}
    monkeypatch.setattr(trial.qb, '_admin', lambda request: None)
    monkeypatch.setattr(trial.previews, 'preview_invoice', lambda request, number: doc)
    monkeypatch.setattr(trial.numbers, 'get_plan', lambda request: {'saved':True})
    monkeypatch.setattr(trial.connection, 'configuration', lambda request: {
        'edition': 'online', 'authorized': False, 'last_read_only_verification':None,
        'company_id':None, 'company_name':None, 'environment':'sandbox'})
    never_called = Mock(side_effect=AssertionError('Cannot read provider or post from disconnected report'))
    monkeypatch.setattr(trial.sync, 'readiness', never_called)
    result = trial.report(object(), 'invoice', 'JS00044')
    assert result['can_post'] is False
    assert result['automatic_sync_enabled'] is False
    assert result['service_fee_collected'] is False
    assert result['payment_link_generated'] is False
    assert result['passed_count'] == 2
    assert result['total_checks'] == 9
    assert never_called.call_count == 0
    assert result['checks'][-1]['code'] == 'approval'


def test_trial_report_verified_approved_links_are_still_not_postable(monkeypatch):
    doc = {'kind':'supplier_po', 'pds_number':'PO-00022', 'lines':[{'position':1}],
           'source_fingerprint':'b'*64,'total':'350.00','currency':'USD'}
    monkeypatch.setattr(trial.qb, '_admin', lambda request: None)
    monkeypatch.setattr(trial.previews, 'preview_supplier_po', lambda request, number:doc)
    monkeypatch.setattr(trial.numbers, 'get_plan', lambda request: {'saved': True})
    monkeypatch.setattr(trial.connection, 'configuration', lambda request: {
        'edition':'online', 'authorized':True, 'last_read_only_verification':123456,
        'company_id':'12345', 'company_name':'Example PDS', 'environment':'sandbox'})
    monkeypatch.setattr(trial.sync, 'readiness', lambda request, kind, number: {
        'party_match':{'status':'approved_master_link','provider_id':'21'},
        'item_mapping':{'reviewed':1,'total':1,'all_lines_reviewed':True}})
    result = trial.report(object(), 'supplier_po', 'PO-00022')
    assert result['passed_count'] == 5
    assert all(not item['passed'] for item in result['checks'][-4:])
    assert result['can_post'] is False


def test_trial_report_rejects_wrong_type_even_before_source_lookup(monkeypatch):
    monkeypatch.setattr(trial.qb, '_admin', lambda request: None)
    with pytest.raises(HTTPException) as exc:
        trial.report(object(), 'payments', 'JS00044')
    assert exc.value.status_code == 422
