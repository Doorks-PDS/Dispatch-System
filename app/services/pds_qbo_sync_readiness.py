"""5.79: non-posting QuickBooks master-link readiness for prepared documents.

Identity matching is deliberately conservative: an approved link is suggested only
when exactly one active PDS master record matches the prepared party name, and its
saved approval matches the selected QuickBooks company and environment. This is
not permission to post; lines, taxes, terms and duplicates require separate review.
"""
from __future__ import annotations

from fastapi import HTTPException
from app.services import pds_qbo_master_links as master
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_sync_preview as preview


def _norm(value):
    return ' '.join(str(value or '').split()).casefold()


def identify_party(name, rows, links, *, kind, company, environment, source_id=None):
    """Pure reconciliation function. Never guess when source identity is ambiguous."""
    # Prefer an explicit saved source ID for supplier POs; never infer a vendor
    # from a similar display name when the PO already references a profile.
    if source_id:
        matches = [r for r in rows if r.get('active') and r.get('pds_id') == source_id]
        if len(matches) != 1 or _norm(matches[0]['name']) != _norm(name):
            return {'status': 'source_id_name_mismatch', 'provider_id': None}
    else:
        matches = [r for r in rows if r.get('active') and _norm(r.get('name')) == _norm(name)]
    if not name or not matches:
        return {'status': 'source_not_found', 'provider_id': None}
    if len(matches) != 1:
        return {'status': 'ambiguous_source', 'provider_id': None}
    row = matches[0]
    link = links.get(f'{kind}:{row["pds_id"]}')
    if not isinstance(link, dict):
        return {'status': 'approval_required', 'pds_id': row['pds_id'], 'provider_id': None}
    valid = (link.get('kind') == kind and link.get('pds_id') == row['pds_id']
             and link.get('company_id') == company and link.get('environment') == environment
             and link.get('source_name') == row['name'] and _norm(link.get('provider_name')) == _norm(row['name'])
             and master.ID.fullmatch(str(link.get('provider_id') or '')))
    if not valid:
        return {'status': 'stale_or_wrong_company', 'pds_id': row['pds_id'], 'provider_id': None}
    return {'status': 'approved_master_link', 'pds_id': row['pds_id'], 'provider_id': link['provider_id']}


def readiness(request, kind, number):
    qb._admin(request)
    if kind not in ('invoice', 'supplier_po'):
        raise HTTPException(422, 'Unsupported document type')
    doc = (preview.preview_invoice if kind == 'invoice' else preview.preview_supplier_po)(request, number)
    company, environment, _ = master._company(request)
    source_kind = 'customers' if kind == 'invoice' else 'suppliers'
    name = doc['pds_customer'] if kind == 'invoice' else doc['pds_supplier']
    rows = master._sources(request, source_kind)
    links = qb._load(master._path(request))['items']
    # Saved PO supplier IDs are verified against PDS supplier profiles. If a
    # legacy PO has no ID, name-only resolution stays fail-closed on ambiguity.
    source_id = None
    if kind == 'supplier_po':
        from app.services import pds_quickbooks_purchase_orders as po
        current = [r for r in po._rows(request).values() if r.get('number') == doc['pds_number']]
        if len(current) != 1:
            raise HTTPException(409, 'Supplier PO identity requires review')
        source_id = current[0].get('supplier_id') or None
    identity = identify_party(name, rows, links, kind=source_kind,
                              company=company, environment=environment, source_id=source_id)
    from app.services import pds_qbo_line_mappings as line_mapper
    saved_items = qb._load(line_mapper._path(request))['items'].get(f'{kind}:{doc["pds_number"]}')
    item_review = line_mapper.line_summary(doc, saved_items, company=company, environment=environment)
    remaining = ([] if item_review['all_lines_reviewed'] else ['Individual income/expense item mappings'])
    remaining += ['Tax treatment', 'Terms / payment handling',
                  'Current QuickBooks item/account recheck', 'Duplicate check and provider write authorization']
    return {'kind': kind, 'pds_number': doc['pds_number'],
            'source_fingerprint': doc['source_fingerprint'],
            'company_id': company, 'environment': environment,
            'party_name': name, 'party_match': identity,
            'line_count': len(doc['lines']), 'source_supplier_id': source_id,
            'item_mapping': {'reviewed': item_review['mapped_lines'],
                             'total': item_review['total_lines'],
                             'all_lines_reviewed': item_review['all_lines_reviewed']},
            'unresolved': remaining,
            'can_post': False, 'automatic_sync_enabled': False,
            'note': 'Identity reference is a reviewed local hint, not proof of current provider status. Reverify before a future write.'}
