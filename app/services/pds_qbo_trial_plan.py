"""Moses 5.82: fail-closed, read-only trial worksheet for a prepared PDS invoice/PO.

A trial worksheet is NOT a QuickBooks payload or posting authorization. It makes
missing approvals and tax/terms decisions visible before a supervised sandbox
trial; all accounting write endpoints remain absent.
"""
from __future__ import annotations

from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as previews
from app.services import pds_quickbooks_numbering as numbers
from app.services import pds_qbo_connection as connection
from app.services import pds_qbo_sync_readiness as sync


def _check(code, label, passed, detail):
    return {'code': code, 'label': label, 'passed': bool(passed), 'detail': str(detail)}


def report(request, kind: str, number: str):
    qb._admin(request)
    if kind not in ('invoice', 'supplier_po'):
        from fastapi import HTTPException
        raise HTTPException(422, 'Choose an invoice or supplier purchase order')
    doc = (previews.preview_invoice if kind == 'invoice' else previews.preview_supplier_po)(request, number)
    conf = connection.configuration(request)
    plan = numbers.get_plan(request)
    verified = (conf['edition'] == 'online' and conf['authorized'] and
                bool(conf['last_read_only_verification']) and
                conf['company_id'] and conf['environment'] in ('sandbox', 'production'))
    checks = [
        _check('prepared', 'Source document prepared and unchanged', True,
               doc['pds_number'] + ' · fingerprint ' + doc['source_fingerprint'][:12]),
        _check('connection', 'Correct QuickBooks Online company verified', verified,
               (str(conf.get('company_name') or conf.get('company_id') or 'Not connected') +
                ' · ' + str(conf.get('environment') or 'unknown'))),
        _check('numbering', 'Numbering policy reviewed', bool(plan.get('saved')),
               'Verify custom numbering and external DocNumber behavior before a test'),
    ]
    match = {'status': 'not_checked', 'provider_id': None}
    mapping = {'reviewed': 0, 'total': len(doc['lines']), 'all_lines_reviewed': False}
    if verified:
        # Reuse 5.79/5.81 *local* approval checks. This does not query, update,
        # create, or reconcile any provider transaction.
        readiness = sync.readiness(request, kind, doc['pds_number'])
        match = readiness['party_match']
        mapping = readiness['item_mapping']
    checks.extend([
        _check('party', 'Customer/vendor link approved', match.get('status') == 'approved_master_link',
               'QuickBooks ID ' + str(match.get('provider_id')) if match.get('provider_id')
               else 'Approve a verified master-record ID in QuickBooks Hub'),
        _check('lines', 'All document lines linked to approved QuickBooks items',
               bool(mapping['all_lines_reviewed']),
               f"{mapping['reviewed']} of {mapping['total']} saved lines reviewed"),
        _check('tax', 'Tax jurisdiction and QuickBooks tax codes reviewed', False,
               'Match per-line taxable treatment and the QuickBooks tax code; compare totals'),
        _check('terms', 'QuickBooks payment terms and accounting accounts reviewed', False,
               ('Doorks terms: ' + str(doc.get('terms') or 'Not specified'))
               if kind == 'invoice' else 'Review supplier terms and expense/receiving policy'),
        _check('duplicate', 'Live duplicate check and provider transaction ID reviewed', False,
               'Run the separate read-only DocNumber check immediately before any supervised posting'),
        _check('approval', 'Supervised provider write explicitly authorized', False,
               'Posting is disabled in this release; no payment or accounting write is possible'),
    ])
    return {'kind': kind, 'pds_number': doc['pds_number'],
            'source_fingerprint': doc['source_fingerprint'], 'company_id': conf.get('company_id'),
            'environment': conf.get('environment'), 'company_name': conf.get('company_name'),
            'source_total': doc['total'], 'currency': doc.get('currency', 'USD'),
            'checks': checks, 'passed_count': sum(c['passed'] for c in checks),
            'total_checks': len(checks), 'all_checks_passed': False,
            'can_post': False, 'automatic_sync_enabled': False,
            'service_fee_collected': False, 'payment_link_generated': False,
            'note': 'Dry run only. Existing documents and QuickBooks records were not changed.'}
