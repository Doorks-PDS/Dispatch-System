"""5.78: reviewed PDS master-record links to existing QBO IDs.

No imports, merges or provider writes. An approved ID is a local identity link,
not permission to sync a document or to create financial transactions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from urllib.parse import urlencode
from urllib.request import Request as HTTPRequest, urlopen
from urllib.error import HTTPError, URLError

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_qbo_connection as conn
from app.services import pds_qbo_catalog as cat

KINDS = {'customers': ('Customer', 'DisplayName'), 'vendors': ('Vendor', 'DisplayName'),
         'suppliers': ('Vendor', 'DisplayName'), 'items': ('Item', 'Name')}
MAX_SOURCE = 5000
ID = re.compile(r'[0-9]{1,32}\Z')


def _norm(v):
    return ' '.join(str(v or '').split()).casefold()


def _sources(request, kind):
    if kind == 'customers':
        records = request.app.state.crm_store.list_customers()
        name_key = 'company_name'
    elif kind == 'vendors':
        path = Path(request.app.state.data_dir) / 'pds_service_vendors' / 'records.json'
        if not path.exists():
            records = []
        else:
            try:
                records = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise HTTPException(503, 'PDS vendor records require review') from exc
        name_key = 'name'
    elif kind == 'suppliers':
        # Independent purchasing suppliers are not the service-vendor directory.
        # Reading never creates supplier folders or changes legacy records.
        path = Path(request.app.state.data_dir) / 'pds_suppliers' / 'records.json'
        if not path.exists():
            records = []
        else:
            try:
                records = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise HTTPException(503, 'PDS supplier profiles require review') from exc
        name_key = 'name'
    elif kind == 'items':
        from app.routers import data
        value = data._read_json_file(data._parts_path(request), {'items': []})
        if not isinstance(value, dict):
            raise HTTPException(503, 'PDS parts catalog requires review')
        records = value.get('items', [])
        name_key = 'part_number'
    else:
        raise HTTPException(422, 'Invalid PDS master record type')
    if not isinstance(records, list) or len(records) > MAX_SOURCE or any(not isinstance(x, dict) for x in records):
        raise HTTPException(503, 'PDS master records need administrator review')
    rows = []
    for record in records:
        id_ = str(record.get('id') or '').strip()
        name = str(record.get(name_key) or '').strip()
        if id_ and len(id_) <= 120 and name and len(name) <= 200:
            rows.append({'pds_id': id_, 'name': name,
                         'active': record.get('active') is not False,
                         'description': str(record.get('description') or '')[:160] if kind == 'items' else ''})
    if len(rows) != len({x['pds_id'] for x in rows}):
        raise HTTPException(409, 'Duplicate PDS master IDs require review')
    return rows


def _company(request):
    if qb._mode(request) != 'online':
        raise HTTPException(409, 'Select QuickBooks Online')
    configuration = conn.configuration(request)
    if (not configuration.get('authorized') or not configuration.get('last_read_only_verification')
            or configuration.get('environment') != conn._environment()):
        raise HTTPException(409, 'Verify the QuickBooks company before linking')
    company_id = str(configuration['company_id'])
    token, realm = conn._access_token(request)
    if str(realm) != company_id:
        raise HTTPException(409, 'Connected QuickBooks company changed')
    return company_id, conn._environment(), token


def _path(request):
    return Path(request.app.state.data_dir) / 'pds_qbo_master_links.json'


def overview(request, kind, *, start=0, limit=100):
    qb._admin(request)
    if kind not in KINDS or start < 0 or limit < 1 or limit > 100:
        raise HTTPException(422, 'Invalid master list or page')
    company, env, _ = _company(request)
    records = _sources(request, kind)
    saved = qb._load(_path(request))['items']
    output = []
    for row in records[start:start + limit]:
        key = f'{kind}:{row["pds_id"]}'
        link = saved.get(key)
        valid = bool(isinstance(link, dict) and link.get('company_id') == company
                     and link.get('environment') == env and link.get('source_name') == row['name'])
        output.append({**row, 'link_status': ('linked' if valid else 'stale_requires_review' if link else 'unlinked'),
                       'provider_id': link.get('provider_id') if valid else None,
                       'provider_name': link.get('provider_name') if valid else None})
    return {'kind': kind, 'company_id': company, 'environment': env,
            'total': len(records), 'start': start, 'next_start': start + limit if start + limit < len(records) else None,
            'records': output, 'provider_writes': False, 'automatic_sync_enabled': False,
            'notice': 'Existing PDS records are never overwritten. Approved links are local and do not enable sync.'}


def candidates(request, kind, pds_id, *, start=1, limit=100):
    qb._admin(request)
    records = [r for r in _sources(request, kind) if r['pds_id'] == pds_id] if kind in KINDS else []
    if len(records) != 1:
        raise HTTPException(404, 'PDS record not found')
    page = cat.catalog(request, kind, start=start, limit=limit)
    _, name_key = KINDS[kind]
    matches = [{'id': x.get('Id'), 'name': x.get(name_key), 'active': x.get('Active')}
               for x in page['records'] if _norm(x.get(name_key)) == _norm(records[0]['name'])]
    return {'pds_record': records[0], 'kind': kind, 'company_id': page['company_id'],
            'candidates': matches, 'next_start': page['next_start'],
            'search_complete': page['next_start'] is None and start == 1,
            'read_only': True, 'note': 'Exact names are suggestions only. Review the intended provider ID.'}


def approve(request, kind, pds_id, provider_id, *, confirm=False):
    qb._admin(request, mutation=True)
    if not confirm or kind not in KINDS or not ID.fullmatch(str(provider_id or '')):
        raise HTTPException(422, 'Explicit approval and valid QuickBooks ID required')
    source = [r for r in _sources(request, kind) if r['pds_id'] == pds_id]
    if len(source) != 1 or not source[0]['active']:
        raise HTTPException(409, 'Active unique PDS record required')
    company, env, token = _company(request)
    entity, name_field = KINDS[kind]
    host = 'https://sandbox-quickbooks.api.intuit.com' if env == 'sandbox' else 'https://quickbooks.api.intuit.com'
    query = f"SELECT * FROM {entity} WHERE Id = '{provider_id}' MAXRESULTS 2"
    req = HTTPRequest(f'{host}/v3/company/{company}/query?' + urlencode({'query': query}),
                      method='GET', headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=12) as reply:
            raw = reply.read(cat.MAX_PAYLOAD + 1)
        if len(raw) > cat.MAX_PAYLOAD:
            raise ValueError('Provider response too large')
        found = json.loads(raw)['QueryResponse'].get(entity, [])
        if not isinstance(found, list) or len(found) != 1 or not isinstance(found[0], dict):
            raise ValueError('Missing unique provider record')
    except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(502, 'Unable to verify QuickBooks record; nothing saved') from exc
    row = found[0]
    if (str(row.get('Id')) != str(provider_id) or row.get('Active') is not True
            or _norm(row.get(name_field)) != _norm(source[0]['name'])):
        raise HTTPException(409, 'QuickBooks record ID, name, or active status differs')
    path = _path(request)
    key = f'{kind}:{pds_id}'
    new = {'kind': kind, 'pds_id': pds_id, 'source_name': source[0]['name'],
           'provider_id': str(provider_id), 'provider_name': str(row[name_field]),
           'company_id': company, 'environment': env,
           'approved_at': datetime.now(timezone.utc).isoformat(),
           'approved_by': str((request.state.auth_user or {}).get('id') or '')[:120]}
    with qb._lock(path):
        ledger = qb._load(path)
        old = ledger['items'].get(key)
        if old:
            if all(old.get(k) == new[k] for k in ('company_id', 'environment', 'source_name', 'provider_id')):
                return {'status': 'already_linked', 'link': old, 'automatic_sync_enabled': False}
            raise HTTPException(409, 'Existing link differs; resolve in Office review before replacing')
        for other_key, other in ledger['items'].items():
            if not isinstance(other, dict):
                raise HTTPException(503, 'Link ledger needs review')
            if (other_key != key and other.get('kind') == kind and other.get('company_id') == company
                    and other.get('environment') == env and other.get('provider_id') == str(provider_id)):
                raise HTTPException(409, 'QuickBooks ID already linked to another PDS record')
        ledger['items'][key] = new
        qb._save(path, ledger)
    return {'status': 'linked', 'link': new, 'automatic_sync_enabled': False,
            'note': 'Master identity link only. No QuickBooks records or documents were changed.'}
