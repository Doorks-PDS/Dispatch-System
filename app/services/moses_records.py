"""Scoped, read-only Moses record discovery using existing workspace stores.

Never performs writes. This adapter deliberately excludes employee/payroll records
until the application has field-level AI permissions for HR/payroll information.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.routers.workspaces import KINDS, _lock, guard, load, location

# Business collections available to the workspace's office admin. Sensitive
# payroll, employees and adjustment ledgers require a separate privacy review.
COLLECTIONS = {
    'sdc': tuple(k for k in KINDS['sdc']),
    'doorks': tuple(k for k in KINDS['doorks'] if k not in ('employees', 'payroll', 'stock_adjustments')),
}

# Deliberately do not return entire business objects: some records contain
# notes, pasted emails, signed links, credentials, or file contents.
SUMMARY_FIELDS = (
    'id', 'job_number', 'work_order_number', 'order_id', 'order_number',
    'customer', 'customer_name', 'vendor', 'vendor_name', 'name', 'contact',
    'address', 'date', 'scheduled_date', 'scheduled_time', 'status',
    'document_type', 'document_number', 'estimate_number', 'invoice_number',
    'po_number', 'product_name', 'sku', 'category', 'item', 'description',
    'total', 'amount', 'quantity', 'fulfillment_status', 'created_at',
    'updated_at', 'source_estimate_number', 'job_type', 'priority',
)
SEARCH_FIELDS = tuple(k for k in SUMMARY_FIELDS if k not in (
    'created_at', 'updated_at', 'total', 'amount', 'quantity', 'description'))


def _verify(request, collection):
    platform = request.session.get('active_platform')
    if platform not in COLLECTIONS or collection not in COLLECTIONS[platform]:
        raise HTTPException(403, 'Collection is not available to Moses in this workspace')
    guard(request, platform, collection)
    return platform


def _summary(record):
    return {key: str(record[key])[:180] for key in SUMMARY_FIELDS
            if isinstance(record.get(key), (str, int, float))
            and not isinstance(record.get(key), bool)}


def collections(request):
    platform = request.session.get('active_platform')
    if platform not in COLLECTIONS:
        raise HTTPException(403, 'This workspace has a different record system')
    # Guard every collection before enumerating. This must never be callable by
    # a non-admin or a request carrying another workspace's session.
    _verify(request, COLLECTIONS[platform][0])
    return {'workspace': platform, 'collections': list(COLLECTIONS[platform]),
            'read_only': True, 'sensitive_records_excluded': True}


def search(request, collection, query):
    platform = _verify(request, collection)
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 100:
        raise HTTPException(422, 'Search must contain 1–100 characters')
    needle = query.strip().casefold()
    with _lock:
        records = load(location(request, platform, collection))
    matches = [record for record in records if isinstance(record, dict) and
               any(needle in str(record.get(key) or '').casefold() for key in SEARCH_FIELDS)]
    return {'workspace': platform, 'collection': collection, 'matching_count': len(matches),
            'examples_limited_to': 8, 'examples': [_summary(record) for record in matches[:8]],
            'read_only': True}


def details(request, collection, record_id):
    platform = _verify(request, collection)
    if not isinstance(record_id, str) or not 1 <= len(record_id.strip()) <= 80:
        raise HTTPException(422, 'Exact record ID required')
    with _lock:
        records = load(location(request, platform, collection))
    selected = next((record for record in records if isinstance(record, dict)
                     and record.get('id') == record_id.strip()), None)
    if selected is None:
        raise HTTPException(404, 'Record not found in the active workspace')
    return {'workspace': platform, 'collection': collection, 'verified': True,
            'record': _summary(selected), 'read_only': True}
