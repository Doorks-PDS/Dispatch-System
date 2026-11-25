"""5.76 read-only comparison of a prepared PDS party name to QBO catalog.

No automatic linking: a name alone is never sufficient identity evidence.
Provider data is fetched through the existing bounded, verified-company reader.
"""
from __future__ import annotations

import re
from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as preview
from app.services import pds_qbo_catalog as catalog

KINDS = {'invoice': ('customers', 'pds_customer'),
         'supplier_po': ('vendors', 'pds_supplier')}


def _normalized(value):
    # Conservative case/whitespace normalization only; no suffix dropping,
    # fuzzy matching or punctuation rewriting that might merge legal entities.
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def review(request, kind: str, number: str, *, start: int = 1, limit: int = 100):
    qb._admin(request)
    if kind not in KINDS or not 1 <= start <= catalog.MAX_TOTAL or not 1 <= limit <= catalog.MAX_PAGE:
        raise HTTPException(422, 'Invalid review type or page')
    if kind == 'invoice':
        source = preview.preview_invoice(request, number)
    else:
        source = preview.preview_supplier_po(request, number)
    name = str(source.get(KINDS[kind][1]) or '').strip()
    if not name or len(name) > 200:
        raise HTTPException(409, 'Source customer or vendor name must be reviewed first')
    page = catalog.catalog(request, KINDS[kind][0], start=start, limit=limit)
    matches = []
    for entry in page['records']:
        if _normalized(entry.get('DisplayName')) == _normalized(name):
            matches.append({'id': entry.get('Id'), 'name': entry.get('DisplayName'),
                            'active': entry.get('Active')})
    more = page['next_start'] is not None
    return {'kind': kind, 'document_number': source['pds_number'],
            'source_name': name, 'company_id': page['company_id'],
            'environment': page['environment'], 'page_start': start,
            'page_count': page['count'], 'next_start': page['next_start'],
            'exact_name_candidates': matches, 'candidate_count_on_page': len(matches),
            'review_status': 'manual_review_required',
            'search_incomplete': more or start > 1,
            'read_only': True, 'mapping_saved': False,
            'can_post': False, 'automatic_sync_enabled': False,
            'notice': 'Names are not unique IDs. Verify identity and inspect all pages before selecting a QuickBooks record.'}
