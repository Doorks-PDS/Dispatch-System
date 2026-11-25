"""5.81: human-reviewed QuickBooks item links for prepared PDS document lines.

A line mapping is a local audit receipt, not an instruction to post. It is bound
by PDS DocNumber, current prepared-source fingerprint, company/environment and
line position plus description/amount. Provider lookups are GET-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request as HTTPRequest, urlopen
from urllib.error import HTTPError, URLError
import json

from fastapi import HTTPException

from app.services import pds_qbo_catalog as catalog
from app.services import pds_qbo_master_links as master
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as preview

KINDS = ('invoice', 'supplier_po')
ALLOWED_ITEM_TYPES = frozenset(('Service', 'NonInventory', 'Inventory'))
MAX_LINES = 100
MAX_ID = 32


def _path(request):
    return Path(request.app.state.data_dir) / 'pds_qbo_line_approvals.json'


def _document(request, kind, number):
    if kind not in KINDS:
        raise HTTPException(422, 'Invoice or supplier PO required')
    return (preview.preview_invoice if kind == 'invoice' else preview.preview_supplier_po)(request, number)


def _selected_line(doc, position):
    lines = doc.get('lines') or []
    if not isinstance(lines, list) or not 1 <= position <= min(len(lines), MAX_LINES):
        raise HTTPException(422, 'Select a valid document line (1–100)')
    line = lines[position - 1]
    if not isinstance(line, dict) or line.get('position') != position:
        raise HTTPException(409, 'Document line positions require review')
    return line


def _signature(line):
    # Fingerprint invalidates all mappings after a source edit; this also
    # prevents reusing a line approval for a different line position or price.
    return {field: line.get(field) for field in
            ('position', 'description', 'quantity', 'unit_price', 'unit_cost', 'amount', 'taxable_in_pds')
            if field in line}


def _compatible(saved, doc, company, environment):
    return (isinstance(saved, dict)
            and saved.get('fingerprint') == doc['source_fingerprint']
            and saved.get('company_id') == company
            and saved.get('environment') == environment
            and saved.get('kind') == doc['kind']
            and saved.get('number') == doc['pds_number']
            and isinstance(saved.get('lines'), dict))


def line_summary(doc, saved, *, company, environment):
    """Pure, fail-closed summary suitable for tests and a preview UI."""
    mapped = 0
    rows = []
    ok = _compatible(saved, doc, company, environment)
    for position, line in enumerate(doc['lines'], start=1):
        approval = saved['lines'].get(str(position)) if ok else None
        valid = (isinstance(approval, dict)
                 and approval.get('source_line') == _signature(line)
                 and str(approval.get('provider_id') or '').isdigit()
                 and 1 <= len(str(approval['provider_id'])) <= MAX_ID
                 and approval.get('item_type') in ALLOWED_ITEM_TYPES
                 and bool(approval.get('account_ref')))
        if valid:
            mapped += 1
        rows.append({'position': position, 'description': line.get('description', ''),
                     'quantity': line.get('quantity'), 'amount': line.get('amount'),
                     'pds_taxable': line.get('taxable_in_pds') if doc['kind'] == 'invoice' else None,
                     'status': 'approved' if valid else 'stale' if saved is not None and not ok else 'needs_item_review',
                     'provider_id': approval['provider_id'] if valid else None,
                     'provider_name': approval['provider_name'] if valid else None,
                     'provider_type': approval['item_type'] if valid else None,
                     'account_ref': approval['account_ref'] if valid else None})
    return {'kind': doc['kind'], 'pds_number': doc['pds_number'],
            'source_fingerprint': doc['source_fingerprint'], 'company_id': company,
            'environment': environment, 'mapped_lines': mapped, 'total_lines': len(rows),
            'all_lines_reviewed': bool(rows) and mapped == len(rows),
            'lines': rows, 'can_post': False, 'automatic_sync_enabled': False,
            'provider_writes': False,
            'unresolved': ['Tax code/rate and jurisdiction review', 'Terms and accounting settings',
                           'Current provider item status and accounts recheck',
                           'Duplicate transaction check, Office approval, supervised posting test'],
            'note': 'A saved item ID is a historical review receipt. QuickBooks may change; reverify immediately before any future posting.'}


def status(request, kind, number):
    qb._admin(request)
    doc = _document(request, kind, number)
    company, environment, _ = master._company(request)
    if len(doc['lines']) > MAX_LINES:
        raise HTTPException(409, 'Too many lines for manual item mapping review')
    key = f'{kind}:{doc["pds_number"]}'
    saved = qb._load(_path(request))['items'].get(key)
    return line_summary(doc, saved, company=company, environment=environment)


def _provider_item(request, provider_id, company, environment, token):
    """Lookup by validated numeric ID. Never create or modify QuickBooks items."""
    if not isinstance(provider_id, str) or not provider_id.isascii() or not provider_id.isdigit() or not (1 <= len(provider_id) <= MAX_ID):
        raise HTTPException(422, 'Enter an existing numeric QuickBooks item ID')
    host = ('https://sandbox-quickbooks.api.intuit.com' if environment == 'sandbox'
            else 'https://quickbooks.api.intuit.com')
    query = f"SELECT * FROM Item WHERE Id = '{provider_id}' MAXRESULTS 2"
    req = HTTPRequest(f'{host}/v3/company/{company}/query?' + urlencode({'query': query}),
                      method='GET', headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=12) as response:
            raw = response.read(catalog.MAX_PAYLOAD + 1)
        if len(raw) > catalog.MAX_PAYLOAD:
            raise ValueError('Response too large')
        found = json.loads(raw)['QueryResponse'].get('Item', [])
        if not isinstance(found, list) or len(found) != 1 or not isinstance(found[0], dict):
            raise ValueError('Provider item not unique')
    except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(502, 'QuickBooks item verification failed; no approval saved') from exc
    return found[0]


def approve(request, kind, number, position, provider_id, *, confirm=False):
    qb._admin(request, mutation=True)
    if not confirm:
        raise HTTPException(422, 'Explicit item approval required')
    if type(position) is not int or position < 1 or position > MAX_LINES:
        raise HTTPException(422, 'Invalid line position')
    # Identity and source status are refreshed before contacting the provider.
    doc = _document(request, kind, number)
    line = _selected_line(doc, position)
    company, environment, token = master._company(request)
    provider = _provider_item(request, provider_id, company, environment, token)
    if (str(provider.get('Id')) != provider_id or provider.get('Active') is not True
            or provider.get('Type') not in ALLOWED_ITEM_TYPES or not str(provider.get('Name') or '').strip()):
        raise HTTPException(409, 'QuickBooks item is inactive, unsupported or differs from the requested ID')
    account_field = 'IncomeAccountRef' if kind == 'invoice' else 'ExpenseAccountRef'
    account = provider.get(account_field)
    account_id = str(account.get('value') or '') if isinstance(account, dict) else ''
    if not account_id.isascii() or not account_id.isdigit() or len(account_id) > MAX_ID:
        raise HTTPException(409, 'QuickBooks item needs a valid ' + account_field + ' before approval')
    # Recheck source and provider company identity after the network round trip.
    current = _document(request, kind, number)
    current_company, current_env, _ = master._company(request)
    if (current['source_fingerprint'] != doc['source_fingerprint']
            or current_company != company or current_env != environment
            or _signature(_selected_line(current, position)) != _signature(line)):
        raise HTTPException(409, 'Source or QuickBooks company changed during item review')
    now = datetime.now(timezone.utc).isoformat()
    approval = {'source_line': _signature(line), 'provider_id': provider_id,
                'provider_name': str(provider['Name'])[:160], 'item_type': provider['Type'],
                'account_ref': account_id, 'account_role': 'income' if kind == 'invoice' else 'expense',
                'approved_at': now,
                'approved_by': str((request.state.auth_user or {}).get('id') or '')[:120]}
    key = f'{kind}:{doc["pds_number"]}'
    path = _path(request)
    with qb._lock(path):
        ledger = qb._load(path)
        saved = ledger['items'].get(key)
        if saved is not None and not _compatible(saved, current, company, environment):
            raise HTTPException(409, 'Older source/company item approvals require reconciliation before reapproval')
        if saved is None:
            saved = {'kind': kind, 'number': doc['pds_number'],
                     'fingerprint': doc['source_fingerprint'],
                     'company_id': company, 'environment': environment,
                     'lines': {}, 'created_at': now}
        old = saved['lines'].get(str(position))
        if old:
            if old.get('source_line') == approval['source_line'] and old.get('provider_id') == provider_id:
                return {'status': 'already_reviewed', 'mapped_item': old, 'can_post': False}
            raise HTTPException(409, 'Existing line maps to a different QuickBooks item; Office reconciliation required')
        saved['lines'][str(position)] = approval
        ledger['items'][key] = saved
        qb._save(path, ledger)
    return {'status': 'reviewed', 'mapped_item': approval, 'can_post': False,
            'note': 'Saved local item review only. No QuickBooks invoice, PO, bill, or payment posted.'}
