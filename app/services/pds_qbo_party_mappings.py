"""5.77: explicit, company-scoped QBO party approval for prepared documents.

All provider operations are GET-only. Approval stores a local review receipt, never
posts transactions or implies that the remaining accounting mappings are ready.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as previews
from app.services import pds_qbo_catalog as catalog
from app.services import pds_qbo_connection as connection

VALID_ID = re.compile(r'[0-9]{1,32}\Z')
TYPES = {'invoice': ('customers', 'pds_customer'), 'supplier_po': ('vendors', 'pds_supplier')}


def _path(request):
    return Path(request.app.state.data_dir) / 'pds_qbo_party_approvals.json'


def _source(request, kind, number):
    qb._admin(request)
    if kind not in TYPES:
        raise HTTPException(422, 'Unsupported prepared document type')
    source = (previews.preview_invoice if kind == 'invoice' else previews.preview_supplier_po)(request, number)
    name = str(source.get(TYPES[kind][1]) or '').strip()
    fingerprint = str(source.get('source_fingerprint') or '')
    if not name or len(name) > 200 or not re.fullmatch('[a-f0-9]{64}', fingerprint):
        raise HTTPException(409, 'Prepared source name and fingerprint require review')
    return source, name, fingerprint


def _verified_company(request):
    if qb._mode(request) != 'online':
        raise HTTPException(409, 'QuickBooks Online required')
    c = connection.configuration(request)
    if not c.get('authorized') or not c.get('last_read_only_verification') or c.get('environment') != connection._environment():
        raise HTTPException(409, 'Verify the connected QuickBooks company first')
    return str(c['company_id']), str(c['environment'])


def _receipt(request, kind, number):
    source, name, fingerprint = _source(request, kind, number)
    company, env = _verified_company(request)
    key = kind + ':' + source['pds_number']
    saved = qb._load(_path(request))['items'].get(key)
    if not saved:
        return {'status': 'not_approved', 'document_number': source['pds_number'],
                'company_id': company, 'mapping': None, 'can_post': False}
    ok = (saved.get('company_id') == company and saved.get('environment') == env
          and saved.get('source_fingerprint') == fingerprint and saved.get('source_name') == name)
    return {'status': 'approved_for_identity_review' if ok else 'stale_requires_new_approval',
            'document_number': source['pds_number'], 'company_id': company,
            'mapping': saved if ok else None, 'can_post': False,
            'automatic_sync_enabled': False}


def status(request, kind, number):
    qb._admin(request)
    return _receipt(request, kind, number)


def approve(request, kind, number, provider_id, *, confirm=False):
    qb._admin(request, mutation=True)
    if not confirm:
        raise HTTPException(422, 'Explicit mapping approval required')
    if not VALID_ID.fullmatch(str(provider_id or '')):
        raise HTTPException(422, 'Use a valid QuickBooks record ID')
    source, name, fingerprint = _source(request, kind, number)
    company, env = _verified_company(request)
    # Strictly GET-only provider lookup. A candidate must be both active and
    # have the exact normalized identity verified against QBO, not just UI text.
    kind_catalog = TYPES[kind][0]
    entity = catalog.KINDS[kind_catalog][0]
    # Fixed query entity and numeric id; bounded response via shared catalog reader.
    from urllib.parse import urlencode
    from urllib.request import Request as HTTPRequest, urlopen
    from urllib.error import HTTPError, URLError
    import json
    token, realm = connection._access_token(request)
    if str(realm) != company:
        raise HTTPException(409, 'Connected QuickBooks company changed')
    host = ('https://sandbox-quickbooks.api.intuit.com' if env == 'sandbox'
            else 'https://quickbooks.api.intuit.com')
    query = f'SELECT * FROM {entity} WHERE Id = \'{provider_id}\' MAXRESULTS 2'
    req = HTTPRequest(f'{host}/v3/company/{company}/query?'+urlencode({'query': query}),
                      headers={'Authorization':'Bearer '+token,'Accept':'application/json'}, method='GET')
    try:
        with urlopen(req, timeout=12) as reply:
            raw = reply.read(catalog.MAX_PAYLOAD + 1)
        if len(raw) > catalog.MAX_PAYLOAD:
            raise ValueError('Provider response too large')
        records = json.loads(raw)['QueryResponse'].get(entity, [])
        if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
            raise ValueError('Provider record not uniquely identified')
    except (HTTPError, URLError, KeyError, ValueError, TypeError, OSError) as exc:
        raise HTTPException(502, 'Could not verify a unique QuickBooks party; no mapping saved') from exc
    row = records[0]
    def normalized(value):
        return ' '.join(str(value or '').split()).casefold()
    if (str(row.get('Id')) != str(provider_id) or row.get('Active') is not True
            or normalized(row.get('DisplayName')) != normalized(name)):
        raise HTTPException(409, 'Provider name, active status, or ID differs; manual reconciliation required')
    key = kind + ':' + source['pds_number']
    result = {'kind':kind, 'document_number':source['pds_number'], 'source_name':name,
              'source_fingerprint':fingerprint, 'company_id':company,'environment':env,
              'provider_id':str(provider_id),'provider_name':str(row['DisplayName']),
              'reviewer_id':str((request.state.auth_user or {}).get('id') or '')[:120],
              'approved_at':datetime.now(timezone.utc).isoformat()}
    path = _path(request)
    with qb._lock(path):
        ledger = qb._load(path)
        previous = ledger['items'].get(key)
        if previous:
            if all(previous.get(k) == result[k] for k in ('company_id','environment','source_fingerprint','source_name','provider_id')):
                return {'status':'already_approved', 'mapping':previous, 'can_post':False}
            raise HTTPException(409, 'Existing mapping differs; manual reconciliation required')
        for other in ledger['items'].values():
            if not isinstance(other, dict):
                raise HTTPException(503, 'Mapping ledger requires office review')
            # The same QBO party may legitimately appear on multiple documents,
            # but not for conflicting PDS party names in this ledger.
            if (other.get('company_id') == company and other.get('environment') == env
                    and other.get('provider_id') == str(provider_id)
                    and normalized(other.get('source_name')) != normalized(name)):
                raise HTTPException(409, 'QuickBooks party already mapped to a different source name')
        ledger['items'][key] = result
        qb._save(path, ledger)
    return {'status':'approved_for_identity_review', 'mapping':result, 'can_post':False,
            'automatic_sync_enabled':False, 'note':'Identity approval only. Accounting/tax mapping and posting remain disabled.'}
