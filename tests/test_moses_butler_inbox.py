"""Synthetic approval-inbox and PDS-ticket regression tests; no real records."""
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from fastapi import HTTPException
from app.services import moses_butler_flow as butler

ROOT = Path(__file__).resolve().parents[1]


def request(space='doorks', role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id': 'synthetic-admin'}, auth_role=role),
                           session={'active_platform': space})


def test_ticket_buttons_removed_but_only_five_reference_fields_are_inline():
    source = (ROOT / 'static/app.js').read_text(encoding='utf-8')
    ticket = source.split('  function renderJobDetails(container, job, ctx)', 1)[1]
    before_drawer = ticket.split('    btnEdit.addEventListener', 1)[0]
    assert 'Quick Edit Ticket Details' not in before_drawer
    assert 'follow.textContent = "Create Follow-Up Job"' not in before_drawer
    assert 'btnEdit.textContent = "Edit"' in before_drawer
    assert 'function attachInlineJobReferences(fields, job, ctx)' in source
    assert 'apiUpdateJob(job.id, { [key]: next })' in source
    assert 'Server did not confirm the updated field' in source
    assert "input.addEventListener('blur', persist)" in source
    assert "input.addEventListener('keydown', event =>" in source
    helper = source.split('  function attachInlineJobReferences', 1)[1].split('  function renderJobDetails', 1)[0]
    for key in ('po_number', 'estimate_number', 'sent_quote_number', 'quote_assigned_to', 'invoice_number'):
        assert "'" + key + "'" in helper
    import re
    map_entries = re.findall(r"\['[^']+', '(po_number|estimate_number|sent_quote_number|quote_assigned_to|invoice_number)'\]", helper)
    assert len(map_entries) == 5 and len(set(map_entries)) == 5


def test_pds_inbox_is_workspace_scoped(monkeypatch):
    proposal = {'id': 'a'*32, 'kind': 'pds_job_status', 'record_id': 'pds-1',
                'state': 'pending', 'requested_at': '2026-11-15T00:00:00Z'}
    monkeypatch.setitem(sys.modules, 'app.services.moses_pds_actions',
                        SimpleNamespace(pending=lambda req: {'proposals':[proposal]}))
    answer = butler.pending_actions(request('pds'))
    assert answer['count'] == 1
    assert answer['proposals'][0]['butler_action'] == 'job_status'
    assert answer['proposals'][0]['executed'] is False
    assert 'decide' not in answer['proposals'][0]
    with pytest.raises(HTTPException) as exc:
        butler.pending_actions(request('pds', 'technician'))
    assert exc.value.status_code == 403


def test_doorks_inbox_aggregates_existing_approval_ledgers(monkeypatch):
    base = {'id': 'b'*32, 'kind': 'draft_purchase_order', 'record_id': 'vendor-1',
            'state': 'pending', 'requested_at': '2026-11-14'}
    receiving = {'id': 'c'*32, 'kind': 'receive_purchase_order', 'po_id': 'po-1',
                 'state': 'needs_review', 'created_at': '2026-11-15'}
    bill = {'id': 'd'*32, 'po_id': 'po-2', 'platform': 'doorks',
            'state': 'pending', 'created_at': '2026-11-13'}
    monkeypatch.setitem(sys.modules, 'app.services.moses_actions',
                        SimpleNamespace(pending=lambda req, platform: {'proposals':[base]}))
    monkeypatch.setitem(sys.modules, 'app.services.moses_receiving_actions',
                        SimpleNamespace(pending=lambda req: {'proposals':[receiving]}))
    monkeypatch.setitem(sys.modules, 'app.services.moses_supplier_bill_actions',
                        SimpleNamespace(pending=lambda req: {'proposals':[bill]}))
    out = butler.pending_actions(request())
    assert out['count'] == 3
    assert {p['butler_action'] for p in out['proposals']} == {'purchase_order','receiving','supplier_bill'}
    assert out['proposals'][0]['butler_action'] == 'receiving'
    assert out['proposals'][0]['state'] == 'needs_review'
    assert all(p['executed'] is False for p in out['proposals'])
