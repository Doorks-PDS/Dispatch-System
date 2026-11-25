"""Moses 5.75: read-only QuickBooks DocNumber collision preflight.

This is a *warning*, not an idempotent write barrier: QuickBooks may contain
transactions with a missing/renumbered DocNumber or concurrent updates. Never
use this endpoint alone to authorize posting.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as HTTPRequest, urlopen

from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_purchase_orders as po
from app.services import pds_qbo_connection as connection
from app.services import pds_quickbooks_sync_preview as preview

KINDS = {'invoice': 'Invoice', 'supplier_po': 'PurchaseOrder'}
MAX_RESPONSE = 512 * 1024


def check(request, kind: str, number: str):
    qb._admin(request)  # Strict Office Admin boundary for QBO information.
    if kind not in KINDS:
        raise HTTPException(422, 'Unsupported QuickBooks transaction type')
    number = str(number or '').strip().upper()
    validator = qb.INVOICE_RE if kind == 'invoice' else po.PO_RE
    if not validator.fullmatch(number):
        raise HTTPException(422, 'Enter a valid existing Doorks document number')
    # Requires prepared, unchanged PDS source. Any stale document blocks lookups.
    if kind == 'invoice':
        preview.preview_invoice(request, number)
    else:
        preview.preview_supplier_po(request, number)
    if qb._mode(request) != 'online':
        raise HTTPException(409, 'Select QuickBooks Online first')
    config = connection.configuration(request)
    if not (config.get('authorized') and config.get('last_read_only_verification')
            and config.get('environment') == connection._environment()):
        raise HTTPException(409, 'Verify the correct QuickBooks company first')
    token, realm = connection._access_token(request)
    if str(realm) != str(config.get('company_id') or ''):
        raise HTTPException(409, 'QuickBooks company mismatch; verify again')
    # Numeric/alphanumeric document-number grammar enforced above; SQL quotes,
    # whitespace, and operators cannot be injected into the fixed query.
    entity = KINDS[kind]
    statement = f"SELECT * FROM {entity} WHERE DocNumber = '{number}' MAXRESULTS 10"
    host = ('https://sandbox-quickbooks.api.intuit.com' if connection._environment() == 'sandbox'
            else 'https://quickbooks.api.intuit.com')
    url = f'{host}/v3/company/{realm}/query?' + urlencode({'query': statement, 'minorversion': '75'})
    req = HTTPRequest(url, headers={'Authorization': 'Bearer ' + token,
                                    'Accept': 'application/json'}, method='GET')
    try:
        with urlopen(req, timeout=12) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError('Provider response too large')
        data = json.loads(raw)
        records = data['QueryResponse'].get(entity, [])
        if not isinstance(records, list) or len(records) > 10 or not all(isinstance(x, dict) for x in records):
            raise ValueError('Unexpected QuickBooks response')
        # Only expose safe identifiers. Don't return bill-to, email or payment details.
        matches = [{'id': str(x.get('Id') or '')[:60],
                    'doc_number': str(x.get('DocNumber') or '')[:60],
                    'sync_token': str(x.get('SyncToken') or '')[:60]}
                   for x in records]
    except (HTTPError, URLError, OSError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(502, 'QuickBooks duplicate check failed; do not proceed with sync') from exc
    return {'kind': kind, 'document_number': number, 'company_id': realm,
            'environment': connection._environment(), 'collision_found': bool(matches),
            'match_count': len(matches), 'matches': matches,
            'review_required': True, 'read_only': True, 'provider_write_performed': False,
            'can_post': False, 'automatic_sync_enabled': False,
            'notice': ('Potential duplicate: reconcile this document with the QuickBooks record before posting.'
                       if matches else 'No exact DocNumber match. Manual matching and provider-side duplicate protection are still required.')}
