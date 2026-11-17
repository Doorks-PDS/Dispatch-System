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
    result = {'workspace': platform, 'kind': kind, 'proposal_id': proposal_id,
              'record_id': str(p.get('record_id') or p.get('po_id') or '')[:80],
              'state': state, 'executed': state == 'executed',
              'approval_required': state in ('pending', 'needs_review'),
              'requires_manual_review': state in ('executing', 'uncertain', 'needs_review'),
              'requested_at': p.get('requested_at') or p.get('created_at'),
              'decided_at': p.get('decided_at'),
              'confirmed_at': p.get('confirmed_at'),
              'note': ('Saved proposal ledger confirms execution; external delivery or payment requires separate verification.'
                       if state == 'executed' else 'No completed execution confirmed')}
    # A completed proposal is an historical fact. Also show whether the current
    # PDS job still reflects the change; it may have been edited since approval.
    # Never assert present-day business state from a ledger entry alone.
    if platform == 'pds' and kind == 'job_status' and state == 'executed':
        store = getattr(request.app.state, 'calendar_store', None)
        try:
            job = store.get_job(p['record_id']) if store is not None else None
        except (KeyError, OSError, TypeError, ValueError):
            job = None
        actual = str(job.get('status') or '') if isinstance(job, dict) and str(job.get('id')) == p['record_id'] else ''
        expected = str(p.get('new_status') or '')
        result['current_record_matches'] = bool(actual and expected and actual == expected)
        result['current_status'] = actual or None
        result['approved_status'] = expected or None
        if not result['current_record_matches']:
            result['requires_manual_review'] = True
            result['note'] = 'The saved action was executed, but the current job no longer confirms that status. Review the ticket.'
    return result


def decide(request, kind: str, proposal_id: str, approve: bool):
    """HTTP-only human decision; never expose this function as an AI model tool."""
    platform = _scope(request, kind)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Approval or rejection must be explicit')
    # Only a pending, exact-kind proposal can be decided. A repeat click after
    # an uncertain response must never invoke a second backend execution.
    before = receipt(request, kind, proposal_id)
    if before['state'] != 'pending':
        raise HTTPException(409, 'Proposal is no longer pending; inspect its receipt before retrying')
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
    if not isinstance(outcome, dict):
        raise HTTPException(500, 'Action backend returned no decision result; review saved receipt')
    if outcome.get('proposal_id') not in (None, proposal_id):
        raise HTTPException(500, 'Action backend returned a different proposal receipt')
    if outcome.get('executed') is True and saved['executed'] is not True:
        raise HTTPException(500, 'Execution could not be verified against saved ledger')
    if approve and outcome.get('executed') is True and platform == 'pds' and kind == 'job_status' and saved.get('current_record_matches') is False:
        raise HTTPException(409, 'Saved action executed, but current PDS job requires manual review')
    if not approve and (saved['state'] != 'rejected' or saved['executed']):
        raise HTTPException(500, 'Rejection was not confirmed in saved ledger')
    return saved


def next_step(request, kind: str, proposal_id: str):
    """Verified, read-only continuation for an executed Doorks work-order creation.

    Do not trust a chat claim or a returned ID alone: the existing saved action
    must have executed, and the actual work order must link to that exact action.
    """
    platform = _scope(request, kind)
    if platform == 'doorks' and kind == 'estimate_draft':
        # No conversational guesses. Follow the exact executed proposal to the
        # immutable Moses linkage on the actual saved estimate.
        saved = receipt(request, kind, proposal_id)
        if saved['state'] != 'executed' or not saved['executed']:
            return {'available': False, 'reason': 'Estimate creation is not confirmed executed'}
        p = _proposal(request, platform, kind, proposal_id)
        estimate_id = str(p.get('estimate_id') or '')
        if not 1 <= len(estimate_id) <= 80:
            return {'available': False, 'reason': 'Saved estimate reference unavailable'}
        from app.routers.workspaces import location, load
        from app.services.moses_actions import _locate
        from decimal import Decimal, InvalidOperation
        docs = load(location(request, platform, 'estimates_invoices'))
        estimate = _locate(docs, estimate_id)
        if (not isinstance(estimate, dict) or str(estimate.get('id') or '') != estimate_id
                or str(estimate.get('source_moses_proposal_id') or '') != proposal_id
                or str(estimate.get('source_work_order_id') or '') != str(p.get('record_id') or '')
                or str(estimate.get('document_type') or '').casefold() != 'estimate'
                or str(estimate.get('customer_id') or '') != str(p.get('details', {}).get('customer_id') or '')):
            return {'available': False, 'reason': 'Estimate does not match the executed proposal'}
        if str(estimate.get('status') or '').casefold() != 'approved':
            return {'available': False, 'reason': 'Review and approve the estimate before invoicing'}
        if (estimate.get('requires_number_assignment') or estimate.get('pricing_required')
                or not re.fullmatch(r'RE[0-9]{5,}', str(estimate.get('document_number') or ''))):
            return {'available': False, 'reason': 'Estimate pricing or official number is not finalized'}
        from app.routers.workspaces import _moses_estimate_review_fingerprint
        if (not estimate.get('pricing_review_fingerprint') or
                estimate.get('pricing_review_fingerprint') != _moses_estimate_review_fingerprint(estimate)):
            return {'available': False, 'reason': 'Estimate changed after pricing review'}
        try:
            amount = Decimal(str(estimate.get('total', estimate.get('amount', ''))))
            if not amount.is_finite() or amount <= 0:
                raise ValueError('nonpositive total')
        except (ValueError, TypeError, InvalidOperation):
            return {'available': False, 'reason': 'Estimate total has not been verified'}
        work_order = _locate(load(location(request, platform, 'work_orders')), str(p.get('record_id') or ''))
        if (not isinstance(work_order, dict)
                or str(work_order.get('customer_id') or '') != str(estimate.get('customer_id') or '')):
            return {'available': False, 'reason': 'Source work-order customer association changed'}
        if any(isinstance(d, dict) and str(d.get('source_estimate_id') or '') == estimate_id
               and str(d.get('document_type') or '').casefold() == 'invoice' for d in docs):
            return {'available': False, 'reason': 'A linked invoice already exists'}
        from app.services import moses_actions
        _, proposal_path, _ = moses_actions._paths(request, platform)
        proposals = moses_actions._read(proposal_path)
        if any(isinstance(a, dict) and a.get('kind') == 'estimate_to_draft_invoice'
               and a.get('record_id') == estimate_id
               and a.get('state') in ('pending', 'executing', 'needs_review') for a in proposals):
            return {'available': False, 'reason': 'An invoice proposal already awaits review'}
        return {'available': True, 'workspace': platform, 'next_kind': 'estimate_to_invoice',
                'record_id': estimate_id, 'label': 'Prepare draft invoice for approval',
                'approval_required': True, 'automatic_execution': False,
                'note': 'Approved estimate verified. A separate approval creates an UNSENT draft invoice.'}
    if platform != 'doorks' or kind != 'new_work_order':
        return {'available': False, 'reason': 'No automatic continuation for this action'}
    saved = receipt(request, kind, proposal_id)
    if saved['state'] != 'executed' or not saved['executed']:
        return {'available': False, 'reason': 'The prior action is not confirmed executed'}
    p = _proposal(request, platform, kind, proposal_id)
    work_order_id = str(p.get('work_order_id') or '')
    if not 1 <= len(work_order_id) <= 80:
        return {'available': False, 'reason': 'Saved work order reference unavailable'}
    from app.routers.workspaces import location, load
    from app.services.moses_actions import _locate
    work_order = _locate(load(location(request, platform, 'work_orders')), work_order_id)
    if (not isinstance(work_order, dict)
            or str(work_order.get('id') or '') != work_order_id
            or str(work_order.get('source_moses_proposal_id') or '') != proposal_id):
        return {'available': False, 'reason': 'Work order does not match the completed action'}
    if str(work_order.get('customer_id') or '') != str(p.get('record_id') or ''):
        return {'available': False, 'reason': 'Saved customer association changed'}
    # Do not offer another AI draft if one was generated, even if the proposal
    # ledger was recovered, or if a proposal is awaiting review.
    docs = load(location(request, platform, 'estimates_invoices'))
    if any(isinstance(d, dict) and d.get('source_work_order_id') == work_order_id
           and d.get('source_moses_proposal_id') for d in docs):
        return {'available': False, 'reason': 'An AI-prepared estimate already exists; review it'}
    from app.services import moses_actions
    _, proposal_path, _ = moses_actions._paths(request, platform)
    proposals = moses_actions._read(proposal_path)
    if any(isinstance(a, dict) and a.get('kind') == 'draft_work_order_estimate'
           and a.get('record_id') == work_order_id
           and a.get('state') in ('pending', 'executing', 'needs_review') for a in proposals):
        return {'available': False, 'reason': 'An estimate proposal already awaits review'}
    return {'available': True, 'workspace': platform, 'next_kind': 'estimate_draft',
            'record_id': work_order_id, 'label': 'Prepare unpriced estimate draft',
            'approval_required': True, 'automatic_execution': False,
            'note': 'A separate approval creates an unpriced draft. Pricing and issuance require office review.'}


def prepare_next_step(request, kind: str, proposal_id: str):
    """A human-requested second proposal; never approves or executes actions."""
    next_action = next_step(request, kind, proposal_id)
    if not next_action.get('available'):
        raise HTTPException(409, next_action.get('reason') or 'Next step unavailable')
    # prepare() rechecks the exact existing record and the existing backend
    # enforces duplicate, customer and record-version protection under its lock.
    result = prepare(request, next_action['next_kind'], next_action['record_id'], {})
    return {**result, 'continued_from_proposal_id': proposal_id}


def ready_continuations(request):
    """Discover verified invoice handoffs after Moses has been reopened.

    Reads the existing proposal ledger; never prepares or executes an action.
    """
    platform = _scope(request)
    if platform != 'doorks':
        return {'items': [], 'count': 0}
    from app.services import moses_actions
    _, proposal_path, _ = moses_actions._paths(request, platform)
    proposals = moses_actions._read(proposal_path)
    items = []
    for p in reversed(proposals[-200:]):
        if not isinstance(p, dict) or p.get('kind') != 'draft_work_order_estimate' or p.get('state') != 'executed':
            continue
        pid = str(p.get('id') or '')
        if not re.fullmatch(r'[a-f0-9]{32}', pid):
            continue
        step = next_step(request, 'estimate_draft', pid)
        if step.get('available'):
            items.append({'id': pid, 'butler_action': 'estimate_draft',
                          'kind': 'draft_work_order_estimate', 'record_id': p.get('record_id'),
                          'state': 'executed', 'workspace': platform,
                          'next_step': step})
        if len(items) >= 20:
            break
    return {'items': items, 'count': len(items), 'read_only': True}


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
