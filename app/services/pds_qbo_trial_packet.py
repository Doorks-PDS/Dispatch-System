"""Moses 5.83: Office Admin review packet for a single prepared PDS accounting document.

No QuickBooks create/update/delete, payments, transfers, email, or audit approvals.
The generated provider-shaped draft is deliberately incomplete until tax/terms,
item state, totals, numbering and a supervised posting policy are verified.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import time

from fastapi import HTTPException

from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as preview
from app.services import pds_quickbooks_numbering as numbering
from app.services import pds_qbo_connection as connection
from app.services import pds_qbo_sync_readiness as sync
from app.services import pds_qbo_line_mappings as line_mapper
from app.services import pds_qbo_collision_check as collisions
from app.services import pds_qbo_trial_plan as trial

CENT = Decimal('0.01')
ID = re.compile(r'[0-9]{1,32}\Z')
MAX_LINES = 100
KINDS = ('invoice', 'supplier_po')


def _decimal(value):
    try:
        item = Decimal(str(value))
        if not item.is_finite():
            raise InvalidOperation
        return item
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(409, 'Source line amount requires Office review')


def _amount_checks(doc):
    lines = doc.get('lines') or []
    if not isinstance(lines, list) or not 1 <= len(lines) <= MAX_LINES:
        return {'passed': False, 'detail': 'One to 100 valid line items required'}
    try:
        total = Decimal('0')
        for line in lines:
            qty = _decimal(line.get('quantity'))
            price = _decimal(line.get('unit_price') if doc['kind'] == 'invoice' else line.get('unit_cost'))
            amount = _decimal(line.get('amount'))
            if qty <= 0 or price < 0 or amount < 0 or (qty * price).quantize(CENT, rounding=ROUND_HALF_UP) != amount:
                return {'passed': False, 'detail': 'Line quantities, rates or rounded amounts require review'}
            total += amount
        expected = _decimal(doc.get('subtotal')).quantize(CENT, rounding=ROUND_HALF_UP)
        if total.quantize(CENT, rounding=ROUND_HALF_UP) != expected:
            return {'passed': False, 'detail': 'Sum of line items differs from the prepared PDS subtotal'}
        if _decimal(doc.get('total')) < 0:
            return {'passed': False, 'detail': 'Prepared PDS total is negative'}
        return {'passed': True, 'detail': f'{len(lines)} lines equal prepared subtotal {expected:.2f} USD'}
    except (HTTPException, KeyError, AttributeError):
        return {'passed': False, 'detail': 'Saved document totals require accounting review'}


def _api_draft(doc, party_id, mapping, policies):
    """Return only a provider-shaped *unpostable* draft from verified local approvals.

    Never guess missing refs. Do not set tax, terms or payment fields. No token or
    Authorization header is returned. A draft is not a valid posting request.
    """
    rows = mapping.get('lines') or []
    if (not ID.fullmatch(str(party_id or '')) or len(rows) != len(doc['lines'])
            or not rows or any(row.get('status') != 'approved' or
                            not ID.fullmatch(str(row.get('provider_id') or '')) for row in rows)):
        return None
    ref_key = 'CustomerRef' if doc['kind'] == 'invoice' else 'VendorRef'
    detail_type = 'SalesItemLineDetail' if doc['kind'] == 'invoice' else 'ItemBasedExpenseLineDetail'
    details_key = detail_type
    lines = []
    for src, link in zip(doc['lines'], rows):
        price = _decimal(src['unit_price'] if doc['kind'] == 'invoice' else src['unit_cost'])
        qty = _decimal(src['quantity'])
        line = {
            'Description': str(src.get('description') or '')[:1000],
            'Amount': float(_decimal(src['amount'])),
            'DetailType': detail_type,
            details_key: {'ItemRef': {'value': str(link['provider_id'])},
                          'Qty': float(qty), 'UnitPrice': float(price)},
        }
        lines.append(line)
    draft = {ref_key: {'value': str(party_id)}, 'Line': lines,
             'PrivateNote': ('PDS source ' + str(doc['pds_number']))[:100]}
    policy = policies.get(doc['kind'])
    if policy == 'request_doorks_number':
        draft['DocNumber'] = str(doc['pds_number'])
    # TxnDate must be reviewed as well; do not guess a date format.
    return draft


def packet(request, kind, number, *, check_duplicates=False):
    qb._admin(request)
    if kind not in KINDS:
        raise HTTPException(422, 'Choose invoice or supplier purchase order')
    doc = (preview.preview_invoice if kind == 'invoice' else preview.preview_supplier_po)(request, number)
    report = trial.report(request, kind, doc['pds_number'])
    config = connection.configuration(request)
    policies = numbering.get_plan(request)
    amounts = _amount_checks(doc)
    verified_at = config.get('last_read_only_verification')
    # Earlier company verification does not prove company state today.
    recently_verified = bool(isinstance(verified_at, (int, float)) and
                             0 <= time.time() - verified_at <= 24 * 60 * 60)
    connected = bool(config.get('authorized') and config.get('edition') == 'online' and
                     config.get('company_id') and recently_verified and
                     config.get('environment') == connection._environment())
    blockers = []
    if not connected:
        blockers.append('Authorize and reverify the intended QuickBooks company within 24 hours')
    if not policies.get('saved'):
        blockers.append('Save and verify QuickBooks numbering preferences')
    if not amounts['passed']:
        blockers.append('Reconcile prepared PDS line amounts and subtotal')
    party = {'status': 'not_checked', 'provider_id': None}
    mapping = {'lines': [], 'mapped_lines': 0, 'total_lines': len(doc.get('lines') or []), 'all_lines_reviewed': False}
    if connected:
        local = sync.readiness(request, kind, doc['pds_number'])
        party = local.get('party_match') or party
        mapping = line_mapper.status(request, kind, doc['pds_number'])
    if party.get('status') != 'approved_master_link' or not ID.fullmatch(str(party.get('provider_id') or '')):
        blockers.append('Approve a unique current customer/vendor master ID')
    if not mapping.get('all_lines_reviewed'):
        blockers.append('Approve every income/expense item reference')
    duplicate = {'status': 'not_requested', 'collision_found': None}
    if check_duplicates:
        if not connected:
            blockers.append('Cannot check provider duplicates until verified and connected')
        else:
            found = collisions.check(request, kind, doc['pds_number'])
            duplicate = {'status': 'checked', 'collision_found': found['collision_found'],
                         'match_count': found['match_count'], 'matches': found['matches']}
            if found['collision_found']:
                blockers.append('Existing QuickBooks document number collision; stop and reconcile')
    else:
        blockers.append('Run a fresh provider duplicate check before supervised trial')
    # Intuit may recompute sales tax and customer terms at create time.
    blockers += [
        'Accountant must confirm tax codes, jurisdiction, and QuickBooks-calculated totals',
        'Accountant must verify payment/supplier terms and account posting rules',
        'Reverify provider item, customer/vendor status and account references immediately before posting',
        'Supervised transaction write and idempotent recovery are not enabled',
    ]
    draft = None
    if connected and amounts['passed'] and mapping.get('all_lines_reviewed'):
        draft = _api_draft(doc, party.get('provider_id'), mapping, policies.get('policies') or {})
    # A draft can be useful to compare line shape, but MUST NEVER be posted.
    return {
        'release': '5.83', 'kind': kind, 'pds_number': doc['pds_number'],
        'source_fingerprint': doc['source_fingerprint'],
        'company_id': config.get('company_id'), 'company_name': config.get('company_name'),
        'environment': config.get('environment'), 'recently_verified': recently_verified,
        'source_amounts': {'subtotal': str(doc.get('subtotal')), 'tax': str(doc.get('tax')),
                           'total': str(doc.get('total')), 'amount_check': amounts},
        'number_policy': (policies.get('policies') or {}).get(kind),
        'party': party, 'mapped_lines': mapping.get('mapped_lines', 0),
        'total_lines': mapping.get('total_lines', len(doc['lines'])),
        'line_review': mapping.get('lines') or [],
        'duplicate_check': duplicate,
        'trial_worksheet': report['checks'],
        'provider_shape_draft': draft,
        'draft_is_safe_to_post': False,
        'blockers': list(dict.fromkeys(blockers)),
        'can_post': False, 'sync_enabled': False,
        'payment_link_enabled': False, 'service_fee_charged': False,
        'provider_write_performed': False,
        'notes': ('Read-only review/export packet. QBO-shaped draft intentionally omits tax, terms, '
                  'provider rechecks and idempotent posting authorization. Never submit it to the API.'),
    }


def setup_diagnostics(request):
    """Read-only checklist using the already configured connection service."""
    qb._admin(request)
    config = connection.configuration(request)
    checks = config.get('checks') or {}
    required = {
        'PDS_QBO_ENVIRONMENT': 'sandbox for first connection/test; production only after signoff',
        'PDS_QBO_CLIENT_ID': 'Intuit app Development client ID for sandbox',
        'PDS_QBO_CLIENT_SECRET': 'Intuit app Development secret for sandbox',
        'PDS_QBO_REDIRECT_URI': 'Exact HTTPS callback registered in Intuit app',
        'PDS_QBO_TOKEN_ENCRYPTION_KEY': 'Fernet key stored as server-only secret',
        'DOORKS_SESSION_SECRET': 'Strong, unique, stable application session secret',
    }
    return {'release': '5.83', 'edition': config.get('edition'),
            'environment': config.get('environment'), 'authorized': config.get('authorized'),
            'company_name': config.get('company_name'), 'company_id': config.get('company_id'),
            'last_read_only_verification': config.get('last_read_only_verification'),
            'checks': checks, 'required_environment': required,
            'callback_path': '/pds-quickbooks/oauth/callback',
            'setup_order': [
                'Confirm QuickBooks Online versus Desktop (OAuth supported only for Online)',
                'Create/select a QuickBooks Online sandbox company in Intuit Developer',
                'Register HTTPS redirect on the Intuit Developer app',
                'Configure Render server-only secrets and select sandbox environment',
                'Confirm durable data disk and encryption key are ready',
                'Authorize as Office Admin, then verify the exact sandbox company',
                'Review existing customer, supplier and item lists; approve links',
                'Prepare one test invoice/PO and run a read-only trial packet',
                'Accountant reviews tax, terms, numbering, processing fees and 0.5% fee treatment',
                'Supervised provider posting remains a separate follow-up release',
            ],
            'can_post': False, 'connection_changes_performed': False,
            'provider_write_performed': False, 'payment_link_enabled': False}


def mapping_coverage(request):
    """Count valid PDS -> QBO master links across four distinct directories.

    A valid link here is a LOCAL identity receipt, not a fresh provider check and
    never permission to sync. This avoids merging service vendors with purchasing
    suppliers or treating every PDS part as a QuickBooks income item.
    """
    from app.services import pds_qbo_master_links as master
    qb._admin(request)
    company, env, _ = master._company(request)
    linked = qb._load(master._path(request))['items']
    kinds = ('customers', 'vendors', 'suppliers', 'items')
    counts = {}
    for kind in kinds:
        sources = master._sources(request, kind)
        valid = unlinked = stale = 0
        for item in sources:
            key = f'{kind}:{item["pds_id"]}'
            saved = linked.get(key)
            if not isinstance(saved, dict):
                unlinked += 1
            elif (saved.get('company_id') == company and saved.get('environment') == env
                  and saved.get('source_name') == item['name']
                  and ID.fullmatch(str(saved.get('provider_id') or ''))):
                valid += 1
            else:
                stale += 1
        counts[kind] = {'total': len(sources), 'approved_local_links': valid,
                        'unlinked': unlinked, 'stale_or_wrong_company': stale}
    return {'company_id': company, 'environment': env, 'counts': counts,
            'provider_records_queried': False, 'provider_writes': False,
            'note': ('Counts are saved local review receipts; recheck QBO identities before '
                     'any financial posting. Service vendors and purchasing suppliers remain separate.')}
