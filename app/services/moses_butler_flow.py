"""Moses's guarded request -> proposal -> human decision -> saved receipt bridge.

The source of truth is ALWAYS the existing workspace proposal/action ledger.
This module never writes business records directly or creates a parallel ledger.
A model may prepare a proposal, but cannot approve or execute one.
"""
from __future__ import annotations

import re
from fastapi import HTTPException

# Precise action vocabulary, scoped to an active workspace. No arbitrary method names.
ACTIONS = {
    'pds': {'job_status', 'estimate_scope'},
    'doorks': {'job_status', 'schedule', 'new_work_order', 'estimate_draft',
               'estimate_to_invoice', 'purchase_order', 'catalog_part',
               'receiving', 'supplier_bill'},
    'sdc': {'order_status', 'estimate_to_invoice', 'purchase_order',
            'catalog_part', 'receiving'},
}
PROPOSAL_KINDS = {
    'job_status': {'pds': 'pds_job_status', 'doorks': 'doorks_work_order_status'},
    'order_status': {'sdc': 'sdc_order_status'},
    'schedule': {'doorks': 'doorks_work_order_schedule'},
    'new_work_order': {'doorks': 'draft_doorks_work_order'},
    'estimate_draft': {'doorks': 'draft_work_order_estimate'},
    'estimate_to_invoice': {'doorks': 'estimate_to_draft_invoice', 'sdc': 'estimate_to_draft_invoice'},
    'purchase_order': {'doorks': 'draft_purchase_order', 'sdc': 'draft_purchase_order'},
    'catalog_part': {'doorks': 'create_catalog_part', 'sdc': 'create_catalog_part'},
    'receiving': {'doorks': 'receive_purchase_order', 'sdc': 'receive_purchase_order'},
    'supplier_bill': {'doorks': None},
}
FIELDS = {
    'job_status': ('new_status',), 'order_status': ('new_status',),
    'schedule': ('scheduled_date', 'scheduled_time'),
    'new_work_order': ('description', 'address', 'priority'),
    'estimate_draft': ('notes',), 'estimate_to_invoice': (),
    'purchase_order': ('description', 'quantity', 'unit_cost'),
    'catalog_part': ('part_number', 'description', 'manufacturer', 'supplier',
                     'product_url', 'image_url', 'unit_cost', 'customer_price'),
    'receiving': ('quantity', 'reference', 'notes'),
    'supplier_bill': ('bill_number', 'bill_amount', 'due_date'),
    'estimate_scope': (),
}
REQUIRED = {
    'job_status': ('new_status',), 'order_status': ('new_status',),
    'schedule': ('scheduled_date', 'scheduled_time'),
    'new_work_order': ('description',),
    'purchase_order': ('description', 'quantity', 'unit_cost'),
    'catalog_part': ('part_number', 'description'),
    'receiving': ('quantity', 'reference'),
    'supplier_bill': ('bill_number', 'bill_amount'),
}


def _scope(request, kind: str | None = None):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    workspace = request.session.get('active_platform')
    if getattr(request.state, 'auth_role', None) != 'office_admin' or workspace not in ACTIONS:
        raise HTTPException(403, 'Active workspace office-admin access required')
    if kind is not None and kind not in ACTIONS[workspace]:
        raise HTTPException(403, 'Action is not authorized in this workspace')
    return workspace


def _identifier(value: str, label='record ID') -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 or value != value.strip():
        raise HTTPException(422, 'Exact '+label+' required')
    return value


def capabilities(request):
    platform = _scope(request)
    return {'workspace': platform, 'actions': sorted(ACTIONS[platform]),
            'policy': 'Exact IDs; existing backend permissions; explicit human approval; durable receipt verification',
            'chat_can_approve': False, 'direct_business_writes_from_model': False}


def _confirm_target(request, platform, kind, target_id):
    # No substring/first-match selection in mutation paths. Only exact saved IDs.
    if kind in ('receiving', 'supplier_bill'):
        # Existing PO services perform their own unique PO-number/ID resolution.
        return
    if kind == 'estimate_scope':
        from app.routers.doorks_assistant import _pds_quote_context
        result = _pds_quote_context(request, target_id)
        if not result.get('verified'):
            raise HTTPException(404, 'PDS job was not verified')
        return result
    if platform == 'pds':
        from app.services.moses_pds_actions import _store
        job = _store(request).get_job(target_id)
        if not isinstance(job, dict) or str(job.get('id')) != target_id:
            raise HTTPException(404, 'Exact PDS job not found')
        return
    from app.routers.workspaces import location, load
    collection = ('customers' if kind == 'new_work_order' else
                  'vendors' if kind == 'purchase_order' else
                  'estimates_invoices' if kind == 'estimate_to_invoice' else
                  'work_orders' if platform == 'doorks' and kind in ('job_status', 'schedule', 'estimate_draft') else
                  'orders' if kind == 'order_status' else None)
    if collection:
        rows = load(location(request, platform, collection))
        exact = [r for r in rows if isinstance(r, dict) and str(r.get('id', '')) == target_id]
        if len(exact) != 1:
            raise HTTPException(404, 'Exactly one saved target record required')


def prepare(request, kind: str, record_id: str, details: dict | None = None):
    platform = _scope(request, kind)
    record_id = _identifier(record_id)
    data = details if details is not None else {}
    if not isinstance(data, dict):
        raise HTTPException(422, 'Action details must be an object')
    unexpected = set(data) - set(FIELDS[kind])
    if unexpected:
        raise HTTPException(422, 'Unsupported action parameter')
    missing = [name for name in REQUIRED.get(kind, ()) if name not in data]
    if missing:
        raise HTTPException(422, 'Required action fields missing: '+', '.join(missing))
    _confirm_target(request, platform, kind, record_id)
    if kind == 'estimate_scope':
        from app.routers.doorks_assistant import _pds_quote_context
        report = _pds_quote_context(request, record_id)
        return {'workspace': platform, 'kind': kind, 'record_id': record_id,
                'status': 'read_only', 'executed': False, 'approval_required': False,
                'verified_scope': report, 'note': 'No estimate has been created or priced'}
    if kind == 'job_status' and platform == 'pds':
        from app.services.moses_pds_actions import propose
        result = propose(request, record_id, data['new_status'])
    elif kind in ('job_status', 'order_status'):
        from app.services.moses_actions import propose
        result = propose(request, record_id, data['new_status'], platform=platform)
    elif kind == 'schedule':
        from app.services.moses_actions import propose_schedule
        result = propose_schedule(request, record_id, data['scheduled_date'], data['scheduled_time'])
    elif kind == 'new_work_order':
        from app.services.moses_actions import propose_work_order
        result = propose_work_order(request, record_id, data['description'],
                                    data.get('address', ''), data.get('priority', 'Normal'))
    elif kind == 'estimate_draft':
        from app.services.moses_actions import propose_work_order_estimate
        result = propose_work_order_estimate(request, record_id, data.get('notes', ''))
    elif kind == 'estimate_to_invoice':
        from app.services.moses_actions import propose_invoice
        result = propose_invoice(request, record_id, platform=platform)
    elif kind == 'purchase_order':
        from app.services.moses_actions import propose_purchase_order
        result = propose_purchase_order(request, record_id, data['description'],
                                         data['quantity'], data['unit_cost'], platform=platform)
    elif kind == 'catalog_part':
        from app.services.moses_actions import propose_part
        # Part number is the primary validated identity, not a free-form guessed record.
        if record_id != data['part_number']:
            raise HTTPException(422, 'Record identifier must equal exact part number')
        result = propose_part(request, data['part_number'], data['description'],
                              manufacturer=data.get('manufacturer', ''),
                              supplier=data.get('supplier', ''),
                              product_url=data.get('product_url', ''),
                              image_url=data.get('image_url', ''),
                              unit_cost=data.get('unit_cost'),
                              customer_price=data.get('customer_price'), platform=platform)
    elif kind == 'receiving':
        from app.services.moses_receiving_actions import propose
        result = propose(request, record_id, data['quantity'],
                         data['reference'], data.get('notes', ''))
    elif kind == 'supplier_bill':
        from app.services.moses_supplier_bill_actions import propose
        result = propose(request, record_id, data['bill_number'],
                         data['bill_amount'], data.get('due_date', ''))
    else:
        raise HTTPException(422, 'Unsupported action')
    proposal = result.get('proposal', {})
    pid = proposal.get('id')
    if (not isinstance(pid, str) or not re.fullmatch(r'[0-9a-f]{32}', pid)
            or result.get('executed') is not False or result.get('approval_required') is not True):
        # A backend contract change must stop the agent; never announce success.
        raise HTTPException(500, 'Backend proposal receipt could not be verified')
    # Reuse the existing Moses chat approval presentation; do not place private
    # source records or attachment contents into the chat response.
    if isinstance(getattr(request.state, 'moses_action_proposals', None), list):
        request.state.moses_action_proposals.append({
            'id': pid, 'kind': proposal.get('kind') or kind, 'record_id': record_id,
            'state': 'pending', 'approval_required': True, 'executed': False,
            'butler_action': kind, 'workspace': platform})
    return {'workspace': platform, 'kind': kind, 'record_id': record_id,
            'proposal_id': pid, 'state': 'pending', 'approval_required': True,
            'executed': False, 'next_step': 'Review and approve or reject from the authenticated office interface'}


def _proposal(request, platform, kind, pid):
    if platform == 'pds':
        from app.services import moses_pds_actions as backend
        with backend._lock:
            items = backend._read(backend._file(request))
    elif kind == 'receiving':
        from app.services import moses_receiving_actions as backend
        backend._guard(request)
        items = backend._rows(backend._path(request, platform))
    elif kind == 'supplier_bill':
        from app.services import moses_supplier_bill_actions as backend
        backend.guard(request)
        items = backend.proposals(request)
    else:
        from app.services import moses_actions as backend
        backend._guard(request, platform)
        _, path, _ = backend._paths(request, platform)
        items = backend._read(path)
    matching = [p for p in items if isinstance(p, dict) and p.get('id') == pid]
    if len(matching) != 1:
        raise HTTPException(404, 'Proposal not found in active workspace')
    proposal = matching[0]
    expected = PROPOSAL_KINDS[kind][platform]
    if expected is not None and proposal.get('kind') != expected:
        raise HTTPException(404, 'Action type does not match saved proposal')
    if kind == 'supplier_bill' and (proposal.get('platform') != 'doorks'):
        raise HTTPException(404, 'Supplier bill belongs to another workspace')
    if kind == 'receiving' and proposal.get('platform') != platform:
        raise HTTPException(404, 'Receipt belongs to another workspace')
    return proposal


def receipt(request, kind: str, proposal_id: str):
    platform = _scope(request, kind)
    if kind == 'estimate_scope':
        raise HTTPException(422, 'Read-only scope has no proposal receipt')
    if not isinstance(proposal_id, str) or not re.fullmatch(r'[0-9a-f]{32}', proposal_id):
        raise HTTPException(422, 'Invalid proposal identifier')
    p = _proposal(request, platform, kind, proposal_id)
    state = str(p.get('state') or 'unknown')
    return {'workspace': platform, 'kind': kind, 'proposal_id': proposal_id,
            'record_id': str(p.get('record_id') or p.get('po_id') or '')[:80],
            'state': state, 'executed': state == 'executed',
            'approval_required': state in ('pending', 'needs_review'),
            'requires_manual_review': state in ('executing', 'uncertain', 'needs_review'),
            'requested_at': p.get('requested_at') or p.get('created_at'),
            'decided_at': p.get('decided_at'),
            'confirmed_at': p.get('confirmed_at'),
            'note': ('Verified from existing saved proposal ledger; a completed payment or external delivery must be separately confirmed.'
                     if state == 'executed' else 'No completed execution confirmed')}


def decide(request, kind: str, proposal_id: str, approve: bool):
    """HTTP-only human decision; never expose this function as an AI model tool."""
    platform = _scope(request, kind)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Approval or rejection must be explicit')
    # Check the exact proposal and workspace BEFORE the legacy backend decides it.
    receipt(request, kind, proposal_id)
    if platform == 'pds':
        from app.services.moses_pds_actions import decide as backend
        outcome = backend(request, proposal_id, approve)
    elif kind == 'receiving':
        from app.services.moses_receiving_actions import decide as backend
        outcome = backend(request, proposal_id, approve)
    elif kind == 'supplier_bill':
        from app.services.moses_supplier_bill_actions import decide as backend
        outcome = backend(request, proposal_id, approve)
    else:
        from app.services.moses_actions import decide as backend
        outcome = backend(request, proposal_id, approve, platform=platform)
    saved = receipt(request, kind, proposal_id)
    if outcome.get('executed') is True and saved['executed'] is not True:
        raise HTTPException(500, 'Execution could not be verified against saved ledger')
    return saved


def pending_actions(request):
    """Admin-only approval inbox aggregated from EXISTING proposal stores.

    No new ledger, cross-workspace reads, or model approvals. Current state is
    always read from the backend, not from conversation text.
    """
    platform = _scope(request)
    result = []
    if platform == 'pds':
        from app.services.moses_pds_actions import pending
        source = pending(request).get('proposals', [])
        batches = [(source, {'pds_job_status': 'job_status'})]
    else:
        from app.services.moses_actions import pending
        base = pending(request, platform=platform).get('proposals', [])
        kinds = {name: kind for kind, spaces in PROPOSAL_KINDS.items()
                 for space, name in spaces.items() if space == platform and name}
        batches = [(base, kinds)]
        from app.services.moses_receiving_actions import pending as receipt_pending
        batches.append((receipt_pending(request).get('proposals', []),
                        {'receive_purchase_order': 'receiving'}))
        if platform == 'doorks':
            from app.services.moses_supplier_bill_actions import pending as bill_pending
            batches.append((bill_pending(request).get('proposals', []),
                            {None: 'supplier_bill'}))
    for rows, mappings in batches:
        for item in rows:
            if not isinstance(item, dict) or item.get('state') not in ('pending', 'needs_review'):
                continue
            kind = mappings.get(item.get('kind'))
            if not kind:
                continue
            pid = str(item.get('id') or '')
            if not re.fullmatch(r'[0-9a-f]{32}', pid):
                continue
            result.append({
                'id': pid, 'butler_action': kind, 'kind': item.get('kind') or kind,
                'record_id': str(item.get('record_id') or item.get('po_id') or '')[:80],
                'state': item['state'], 'workspace': platform,
                'requested_at': item.get('requested_at') or item.get('created_at'),
                'executed': False, 'approval_required': True,
            })
    result.sort(key=lambda row: str(row.get('requested_at') or ''), reverse=True)
    return {'workspace': platform, 'proposals': result[:50],
            'count': len(result), 'limited_to': 50,
            'note': 'Every approval is revalidated by its existing business backend.'}
