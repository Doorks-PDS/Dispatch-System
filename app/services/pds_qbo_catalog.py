"""Office Admin-only, strictly read-only QuickBooks Online mapping catalog.

This is an inspection aid, not a synchronization or mapping writer. Results are
bounded, never persisted, and intentionally omit contact/banking details.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as HTTPRequest, urlopen

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_qbo_connection as connection

# Fixed query types and fields; no caller-controlled SQL or provider URL.
KINDS = {
    'customers': ('Customer', ('Id', 'DisplayName', 'Active')),
    'vendors': ('Vendor', ('Id', 'DisplayName', 'Active')),
    'items': ('Item', ('Id', 'Name', 'Type', 'Active', 'IncomeAccountRef', 'ExpenseAccountRef')),
    'accounts': ('Account', ('Id', 'Name', 'AccountType', 'AccountSubType', 'Active')),
    'tax_codes': ('TaxCode', ('Id', 'Name', 'Active')),
    'terms': ('Term', ('Id', 'Name', 'Active')),
}
MAX_PAGE = 100
MAX_TOTAL = 1000
MAX_PAYLOAD = 1024 * 1024


def _clean(value):
    if isinstance(value, dict):
        return str(value.get('value') or '')[:128]
    if isinstance(value, (str, int, float, bool)):
        return value if isinstance(value, bool) else str(value)[:160]
    return None


def catalog(request, kind: str, *, start: int = 1, limit: int = 100):
    qb._admin(request)  # Read access must still be Office Admin for QBO configuration.
    if kind not in KINDS or not (1 <= start <= MAX_TOTAL) or not (1 <= limit <= MAX_PAGE):
        raise HTTPException(422, 'Choose a supported QuickBooks catalog and page')
    if qb._mode(request) != 'online':
        raise HTTPException(409, 'QuickBooks Online must be selected before catalog lookup')
    config = connection.configuration(request)
    if not (config.get('authorized') and config.get('last_read_only_verification')
            and config.get('environment') == connection._environment()):
        raise HTTPException(409, 'Verify your QuickBooks Online company before reviewing provider records')
    token, realm = connection._access_token(request)
    if str(config.get('company_id') or '') != str(realm):
        raise HTTPException(409, 'QuickBooks company changed; verify it again')
    entity, fields = KINDS[kind]
    page_limit = min(limit, MAX_TOTAL - start + 1)
    statement = f'SELECT * FROM {entity} STARTPOSITION {start} MAXRESULTS {page_limit}'
    host = ('https://sandbox-quickbooks.api.intuit.com' if connection._environment() == 'sandbox'
            else 'https://quickbooks.api.intuit.com')
    url = f'{host}/v3/company/{realm}/query?' + urlencode({'query': statement, 'minorversion': '75'})
    req = HTTPRequest(url, headers={'Authorization': 'Bearer ' + token,
                                     'Accept': 'application/json'}, method='GET')
    try:
        with urlopen(req, timeout=12) as response:
            raw = response.read(MAX_PAYLOAD + 1)
        if len(raw) > MAX_PAYLOAD:
            raise ValueError('Provider response exceeded safe size')
        result = json.loads(raw)
        entries = result['QueryResponse'].get(entity, [])
        if not isinstance(entries, list) or len(entries) > page_limit:
            raise ValueError('Unexpected provider catalog shape')
        if not all(isinstance(item, dict) for item in entries):
            raise ValueError('Invalid provider catalog item')
    except (HTTPError, URLError, ValueError, KeyError, TypeError, OSError) as exc:
        raise HTTPException(502, 'QuickBooks catalog request failed; no accounting data was changed') from exc
    rows = [{key: _clean(item.get(key)) for key in fields if key in item} for item in entries]
    more = start + len(rows) <= MAX_TOTAL and len(rows) == page_limit
    return {'kind': kind, 'company_id': realm, 'environment': connection._environment(),
            'start': start, 'page_size': page_limit, 'count': len(rows),
            'next_start': (start + len(rows)) if more else None,
            'records': rows, 'read_only': True, 'provider_write_performed': False,
            'mapping_saved': False, 'automatic_sync_enabled': False,
            'note': 'Use this catalog to review provider IDs before mapping; nothing is matched or synced automatically.'}
