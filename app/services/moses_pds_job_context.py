"""One grounded PDS job context for the existing Moses assistant.

Read-only composition of CalendarStore, DocumentsStore and saved Moses review
records. No speculative joins by customer/address, no cross-workspace access,
no status changes, prices, attachments, or customer email bodies exposed.
"""
from __future__ import annotations
import re
from fastapi import HTTPException


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if (request.session.get('active_platform') != 'pds' or
            getattr(request.state, 'auth_role', None) not in ('office_admin','office','lead')):
        raise HTTPException(403, 'Active PDS office administrator required')
    return getattr(request.app.state, 'calendar_store', None)


def _clip(value, length=180):
    return str(value or '').strip()[:length]


def inspect(request, job_id: str):
    """Inspect an EXACT PDS internal job ID obtained from saved job search."""
    store = _guard(request)
    if not isinstance(job_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', job_id):
        raise HTTPException(422, 'Invalid job identifier')
    if store is None:
        raise HTTPException(503, 'PDS job store is unavailable')
    try:
        job = store.get_job(job_id)
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'PDS job could not be read') from exc
    if not isinstance(job, dict) or str(job.get('id') or '') != job_id:
        raise HTTPException(404, 'Saved PDS job not found')
    number = _clip(job.get('job_number'), 80)
    status = _clip(job.get('status'), 80)
    result = {
        'workspace': 'pds', 'read_only': True,
        'job': {key: _clip(job.get(key), 240) for key in (
            'id', 'job_number', 'customer', 'address', 'status', 'date',
            'estimate_number', 'sent_quote_number', 'invoice_number', 'po_number',
            'quote_assigned_to')},
        'documents': {'available': False, 'count': None, 'items': []},
        'moses_drafts': {'available': False, 'count': None, 'items': []},
        'recommendation': {'ready_to_quote': False, 'form_count': 0,
                           'has_parts_requirements': False, 'has_time_requirements': False},
        'next_steps': [],
        'note': 'Saved records read only. No estimate, approval, email, or job was changed.'
    }
    forms = job.get('completion_forms')
    if isinstance(forms, list):
        result['recommendation']['form_count'] = sum(isinstance(form, dict) for form in forms)
        eligible = [f for f in forms if isinstance(f, dict) and f.get('ready_to_quote') is True]
        result['recommendation']['ready_to_quote'] = bool(eligible)
        result['recommendation']['has_parts_requirements'] = any(bool(str(f.get('parts_required') or '').strip()) for f in eligible)
        result['recommendation']['has_time_requirements'] = any(bool(str(f.get('time_required') or '').strip()) for f in eligible)
    else:
        result['recommendation']['form_count'] = None
    docs_store = getattr(request.app.state, 'documents_store', None)
    if docs_store is not None:
        try:
            docs = docs_store.list_documents(job_id=job_id)
        except (OSError, TypeError, ValueError, KeyError) as exc:
            raise HTTPException(503, 'PDS document index cannot be verified') from exc
        if not isinstance(docs, list):
            raise HTTPException(503, 'PDS document index format invalid')
        # The document store's job_id filter is required, but re-check each row.
        matched = [d for d in docs if isinstance(d, dict) and str(d.get('job_id') or '') == job_id]
        result['documents'] = {'available': True, 'count': len(matched), 'items': [
            {'type': _clip(d.get('type'), 30), 'number': _clip(d.get('number'), 80),
             'created_at': _clip(d.get('created_at'), 50)} for d in matched[:12]]}
    from app.routers.moses_drafts import list_drafts
    drafts = list_drafts(request)
    if not isinstance(drafts, dict) or not isinstance(drafts.get('items'), list):
        raise HTTPException(503, 'Saved Moses draft list invalid')
    matching = [d for d in drafts['items'] if isinstance(d, dict) and str(d.get('job_id') or '') == job_id]
    result['moses_drafts'] = {'available': True, 'count': len(matching), 'items': [
        {'id': _clip(d.get('id'), 80), 'state': _clip(d.get('state'), 50),
         'updated_at': _clip(d.get('updated_at'), 50)} for d in matching[:12]]}
    # These are suggestions only; all write/external actions have their own approval gates.
    if matching and any(d.get('state') == 'pending_review' for d in matching):
        result['next_steps'].append('Review saved Moses quote draft before estimator handoff')
    elif matching and any(d.get('state') == 'ready_for_estimator' for d in matching):
        result['next_steps'].append('Open the existing PDS estimator with the approved saved draft')
    elif result['recommendation']['ready_to_quote'] and not job.get('sent_quote_number'):
        result['next_steps'].append('Prepare a review ticket from the saved technician recommendation')
    if status.casefold() == 'to be invoiced':
        result['next_steps'].append('Review completion and existing invoices before drafting an invoice')
    if status.casefold() == 'parts on order':
        result['next_steps'].append('Check actual PO, receiving, and supplier status before scheduling')
    if job.get('estimate_number') and result['documents']['available'] and not any(
        d.get('type') == 'estimate' and d.get('number') == str(job.get('estimate_number'))
        for d in result['documents']['items']):
        result['next_steps'].append('Estimate reference exists on job but no exact linked estimate appears in the document index')
    if not result['next_steps']:
        result['next_steps'].append('Review the saved job and current status before taking action')
    return result
