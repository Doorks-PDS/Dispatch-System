"""Office Admin-only QuickBooks numbering plan and verified cross-system references.

PDS RE/JS/PO numbers are authoritative local identifiers; never rewrite the saved
PDFs, job references, customer PO numbers or the QuickBooks system counter.
No QuickBooks connection, automatic sync or external transaction is performed here.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb

KINDS = ('estimate', 'invoice', 'supplier_po')
POLICIES = ('request_doorks_number', 'quickbooks_assigns_number')
PATTERNS = {
    'estimate': re.compile(r'RE\d{5,}\Z', re.I),
    'invoice': re.compile(r'JS\d{5,}\Z', re.I),
    'supplier_po': re.compile(r'PO-\d{5,}\Z', re.I),
}
EXAMPLES = {'estimate': 'RE00097', 'invoice': 'JS00021', 'supplier_po': 'PO-00020'}


def _path(request):
    return Path(request.app.state.data_dir) / 'pds_quickbooks_numbering.json'


def _links_path(request):
    return Path(request.app.state.data_dir) / 'pds_quickbooks_verified_refs.json'


def _policies(request):
    path = _path(request)
    if not path.exists():
        return {kind: 'request_doorks_number' for kind in KINDS}, False
    settings = qb._load(path)
    data = settings.get('policies')
    if (not isinstance(data, dict) or set(data) != set(KINDS)
            or any(value not in POLICIES for value in data.values())):
        raise HTTPException(503, 'QuickBooks numbering plan needs administrator review')
    return data, True


def _references(request):
    data = qb._load(_links_path(request))['items']
    if any(not isinstance(record, dict) for record in data.values()):
        raise HTTPException(503, 'QuickBooks reference ledger needs administrator review')
    return data


def get_plan(request):
    qb._admin(request)
    policies, saved = _policies(request)
    references = _references(request)
    edition = qb._mode(request)
    rows = []
    for kind in KINDS:
        local = EXAMPLES[kind]
        policy = policies[kind]
        rows.append({
            'kind': kind, 'doorks_example': local, 'policy': policy,
            'quickbooks_example': local if policy == 'request_doorks_number' else None,
            'quickbooks_number_not_assigned': policy == 'quickbooks_assigns_number',
            'verified_reference_count': sum(1 for r in references.values() if r.get('kind') == kind),
        })
    return {
        'edition': edition, 'saved': saved, 'policies': policies, 'examples': rows,
        'verified_reference_count': len(references),
        'connected_to_quickbooks': False, 'automatic_sync_enabled': False,
        'changes_local_numbers': False, 'writes_external_transactions': False,
        'quickbooks_numbering_preferences_verified': False,
        'requires_collision_check': True,
        'note': ('Keep PDS estimate, invoice and supplier PO numbers. QuickBooks Online '
                 'custom transaction numbering must be checked during connection before requesting '
                 'these numbers. Otherwise let QuickBooks assign its number and keep a verified mapping.'),
    }


def save_plan(request, policies):
    qb._admin(request, mutation=True)
    if (not isinstance(policies, dict) or set(policies) != set(KINDS)
            or any(not isinstance(v, str) or v not in POLICIES for v in policies.values())):
        raise HTTPException(422, 'Choose a numbering policy for each PDS document type')
    path = _path(request)
    with qb._lock(path):
        # Preserve the existing plan until an administrator explicitly saves all three.
        qb._save(path, {'version': 1, 'items': {}, 'policies': policies,
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                        'updated_by': str((request.state.auth_user or {}).get('id') or '')[:120]})
    return get_plan(request)


def verified_reference(request, *, kind, doorks_number, company_id, quickbooks_id,
                       quickbooks_number, checked_against_provider=False):
    """Future adapter hook: record an actual provider-verified object, never a guess.

    Not routed to the browser. Caller must have compared the returned QuickBooks
    object with the correct company, type, source number, customer/vendor and amount.
    These references must not be used to change numbering in PDS records.
    """
    qb._admin(request, mutation=True)
    doorks_number = str(doorks_number or '').strip().upper()
    company_id = str(company_id or '').strip()
    quickbooks_id = str(quickbooks_id or '').strip()
    quickbooks_number = str(quickbooks_number or '').strip()
    if (kind not in KINDS or not PATTERNS[kind].fullmatch(doorks_number)
            or not checked_against_provider or not company_id or not quickbooks_id
            or not quickbooks_number or any(len(s) > 128 for s in (company_id, quickbooks_id, quickbooks_number))):
        raise HTTPException(422, 'Verified company, source document and QuickBooks transaction required')
    # Source record must exist in current PDS business data, with no ambiguous local number.
    if kind == 'supplier_po':
        from app.services.pds_quickbooks_purchase_orders import _source
        sources = [x for x in _source(request) if str(x.get('po_number') or '').upper() == doorks_number]
    else:
        sources = [x for x in request.app.state.documents_store.list_documents()
                   if str(x.get('type') or '').lower() == kind
                   and str(x.get('number') or '').upper() == doorks_number]
    if len(sources) != 1:
        raise HTTPException(409, 'PDS source document must be uniquely verified before linking')
    key = kind + ':' + doorks_number
    path = _links_path(request)
    with qb._lock(path):
        ledger = qb._load(path)
        items = ledger['items']
        target = (company_id, kind, quickbooks_id)
        record = {'kind': kind, 'doorks_number': doorks_number,
                  'quickbooks_company_id': company_id, 'quickbooks_record_id': quickbooks_id,
                  'quickbooks_number': quickbooks_number, 'status': 'provider_verified',
                  'verified_at': datetime.now(timezone.utc).isoformat()}
        old = items.get(key)
        if old:
            if (old.get('quickbooks_company_id'), old.get('kind'), old.get('quickbooks_record_id'),
                old.get('quickbooks_number')) != (company_id, kind, quickbooks_id, quickbooks_number):
                raise HTTPException(409, 'Conflicting QuickBooks number or record; manual reconciliation required')
            return {'record': old, 'duplicate': True}
        if any((r.get('quickbooks_company_id'), r.get('kind'), r.get('quickbooks_record_id')) == target
               for r in items.values() if isinstance(r, dict)):
            raise HTTPException(409, 'QuickBooks transaction already linked to another PDS document')
        if any((r.get('quickbooks_company_id'), r.get('kind'), r.get('quickbooks_number'))
               == (company_id, kind, quickbooks_number) for r in items.values() if isinstance(r, dict)):
            raise HTTPException(409, 'QuickBooks display number already mapped; review for duplicates')
        items[key] = record
        qb._save(path, ledger)
    return {'record': record, 'duplicate': False}
