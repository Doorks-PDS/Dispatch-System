"""Explicit approval and crash-recoverable SDC order status actions.

No model response is approval. SDC-only, office-admin only, feature-flagged.
The existing workspace JSON write helper performs atomic file replacement.
"""
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone, date, time
from hashlib import sha256
from fastapi import HTTPException

STATUSES = ('Open', 'In Production', 'Shipped', 'Delivered')
DOORKS_STATUSES = ('Dispatch', 'Scheduled', 'In Progress', 'To Be Quoted', 'Quote Sent', 'Approved', 'Parts on Order', 'To Be Invoiced', 'Invoiced', 'Complete', 'Cancelled')


def enabled(platform='sdc'):
    flag = 'DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED' if platform == 'doorks' else 'DOORKS_SDC_MOSES_ACTIONS_ENABLED'
    return os.getenv(flag, '').lower().strip() == 'true'


def _guard(request, platform='sdc'):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if platform not in ('sdc', 'doorks') or request.session.get('active_platform') != platform or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active workspace office-admin required')
    if not enabled(platform):
        raise HTTPException(503, 'Moses actions are disabled')


def _actor(request):
    user = request.state.auth_user
    return str(user.get('id') or user.get('username') or 'office_admin') if isinstance(user, dict) else str(user)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _paths(request, platform='sdc'):
    from app.routers.workspaces import location
    kind = 'work_orders' if platform == 'doorks' else 'orders'
    base = location(request, platform, kind).parent
    return base / (kind + '.json'), base / 'moses_action_proposals.json', base / 'moses_action_audit.json'


def _read(path):
    from app.routers.workspaces import load
    return load(path)


def _write(path, records):
    from app.routers.workspaces import save
    save(path, records)


def _version(record):
    return sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _locate(rows, record_id):
    return next((r for r in rows if isinstance(r, dict) and r.get('id') == record_id), None)


def _validate_schedule(scheduled_date, scheduled_time):
    """Use the existing local date/time strings, never interpret as UTC."""
    if not isinstance(scheduled_date, str) or not isinstance(scheduled_time, str):
        raise HTTPException(422, 'Date and time must be strings')
    try:
        if date.fromisoformat(scheduled_date).isoformat() != scheduled_date:
            raise ValueError()
        parsed = time.fromisoformat(scheduled_time)
        if parsed.strftime('%H:%M') != scheduled_time:
            raise ValueError()
    except ValueError:
        raise HTTPException(422, 'Use YYYY-MM-DD and 24-hour HH:MM time')
    return {'scheduled_date': scheduled_date, 'scheduled_time': scheduled_time}


def _assert_schedule_safe(request, order):
    """Do not desynchronize existing vendor assignment or multi-visit records."""
    from app.routers.workspaces import location
    if any(order.get(key) for key in ('visits', 'scheduled_visits', 'visit_history', 'schedule_history')):
        raise HTTPException(409, 'Work order has visit history; reschedule manually')
    assignments = _read(location(request, 'doorks', 'vendor_assignments'))
    identifiers = {str(order.get(k)) for k in ('id', 'job_number', 'work_order_number') if order.get(k)}
    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        if any(str(assignment.get(key)) in identifiers for key in ('work_order_id', 'work_order_number', 'job_number') if assignment.get(key)):
            raise HTTPException(409, 'Linked vendor assignment requires coordinated rescheduling')


def propose_schedule(request, record_id, scheduled_date, scheduled_time):
    _guard(request, 'doorks')
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 80:
        raise HTTPException(422, 'Valid work order ID required')
    updated = _validate_schedule(scheduled_date, scheduled_time)
    from app.routers.workspaces import _lock
    with _lock:
        path, proposals_path, audit_path = _paths(request, 'doorks')
        _reconcile_locked(path, proposals_path, audit_path)
        order = _locate(_read(path), record_id)
        if order is None:
            raise HTTPException(404, 'Work order not found')
        _assert_schedule_safe(request, order)
        old = {key: order.get(key, '') for key in updated}
        if old == updated:
            raise HTTPException(409, 'Work order already has this schedule')
        proposal = {'id': uuid.uuid4().hex, 'kind': 'doorks_work_order_schedule',
                    'record_id': record_id, 'old_schedule': old, 'new_schedule': updated,
                    'record_version': _version(order), 'state': 'pending',
                    'requested_by': _actor(request), 'requested_at': _now()}
        proposals = _read(proposals_path)
        proposals.append(proposal)
        _write(proposals_path, proposals)
        return {'proposal': proposal, 'executed': False, 'approval_required': True}


def propose_invoice(request, record_id, platform='sdc'):
    """Request approval to convert an approved workspace estimate to a draft invoice.

    Reuse the existing workspaces converter and invoice numbering, never fabricate
    a document number or issue/send the resulting draft.
    """
    _guard(request, platform)
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 80:
        raise HTTPException(422, 'Exact estimate ID required')
    from app.routers.workspaces import _lock, location
    with _lock:
        _, proposal_path, audit_path = _paths(request, platform)
        # Reconcile uses the order store for status operations; invoice operations
        # have their own idempotent recovery branch.
        _reconcile_locked(*_paths(request, platform))
        documents = _read(location(request, platform, 'estimates_invoices'))
        source = _locate(documents, record_id)
        if source is None or str(source.get('document_type', '')).casefold() != 'estimate':
            raise HTTPException(404, 'Estimate not found')
        if str(source.get('status', '')).casefold() != 'approved':
            raise HTTPException(409, 'Estimate must be approved first')
        if _linked_invoice(documents, record_id):
            raise HTTPException(409, 'Invoice already exists for this estimate')
        proposals = _read(proposal_path)
        if any(isinstance(x, dict) and x.get('kind') == 'estimate_to_draft_invoice'
               and x.get('record_id') == record_id and x.get('state') in ('pending', 'executing', 'needs_review')
               for x in proposals):
            raise HTTPException(409, 'An invoice proposal for this estimate already awaits review')
        proposal = {'id': uuid.uuid4().hex, 'kind': 'estimate_to_draft_invoice',
                    'record_id': record_id, 'estimate_number': str(source.get('document_number', ''))[:80],
                    'record_version': _version(source), 'state': 'pending',
                    'requested_by': _actor(request), 'requested_at': _now()}
        proposals.append(proposal)
        _write(proposal_path, proposals)
        return {'proposal': proposal, 'approval_required': True, 'executed': False}


def _linked_work_order(rows, proposal_id):
    return next((r for r in rows if isinstance(r, dict) and r.get('source_moses_proposal_id') == proposal_id), None)


def propose_work_order(request, customer_id, description, address='', priority='Normal'):
    """Approval-only request to open a Doorks work order through its existing create API.

    Never copies an unverified customer name from the model; never creates PDS jobs.
    """
    from app.routers.workspaces import _lock, location
    _guard(request, 'doorks')
    if not isinstance(customer_id, str) or not 1 <= len(customer_id) <= 80:
        raise HTTPException(422, 'Verified customer ID is required')
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1500:
        raise HTTPException(422, 'Work description must contain 1-1500 characters')
    if not isinstance(address, str) or len(address) > 500 or not isinstance(priority, str) or priority not in ('Normal', 'Emergency'):
        raise HTTPException(422, 'Invalid address or priority')
    with _lock:
        orders_path, proposals_path, audit_path = _paths(request, 'doorks')
        _reconcile_locked(orders_path, proposals_path, audit_path)
        customer = _locate(_read(location(request, 'doorks', 'customers')), customer_id)
        if not customer or not str(customer.get('name') or customer.get('customer_name') or '').strip():
            raise HTTPException(404, 'Customer not found')
        if customer.get('active') is False or customer.get('deactivated_at'):
            raise HTTPException(409, 'Customer is inactive')
        details = {'customer_id': customer_id,
                   'customer': str(customer.get('name') or customer.get('customer_name'))[:200],
                   'description': description.strip(), 'address': address.strip(),
                   'priority': priority, 'status': 'Dispatch'}
        proposals = _read(proposals_path)
        proposal = {'id': uuid.uuid4().hex, 'kind': 'draft_doorks_work_order',
                    'record_id': customer_id, 'details': details,
                    'record_version': _version(customer), 'state': 'pending',
                    'requested_by': _actor(request), 'requested_at': _now()}
        proposals.append(proposal)
        _write(proposals_path, proposals)
        return {'proposal': proposal, 'approval_required': True, 'executed': False}


def _linked_estimate(rows, proposal_id):
    return next((r for r in rows if isinstance(r, dict)
                 and r.get('source_moses_proposal_id') == proposal_id
                 and str(r.get('document_type', '')).casefold() == 'estimate'), None)


def propose_work_order_estimate(request, work_order_id, notes=''):
    """Propose an explicitly UNPRICED, unissued draft from a verified Doorks job.

    The workspace editor has no server-side estimate sequence yet. Never assign
    an apparently official number or fabricate labor/parts/prices.
    """
    from app.routers.workspaces import _lock, location
    _guard(request, 'doorks')
    if not isinstance(work_order_id, str) or not 1 <= len(work_order_id) <= 80:
        raise HTTPException(422, 'Verified work order ID required')
    if not isinstance(notes, str) or len(notes) > 1500:
        raise HTTPException(422, 'Notes must be 1500 characters or fewer')
    with _lock:
        orders_path, proposal_path, audit_path = _paths(request, 'doorks')
        _reconcile_locked(orders_path, proposal_path, audit_path)
        work_order = _locate(_read(orders_path), work_order_id)
        if not work_order:
            raise HTTPException(404, 'Work order not found')
        customer_id = str(work_order.get('customer_id') or '')
        customer = _locate(_read(location(request, 'doorks', 'customers')), customer_id)
        if not customer or customer.get('active') is False:
            raise HTTPException(409, 'Work order customer could not be verified')
        if str(work_order.get('customer') or '').strip().casefold() != str(customer.get('name') or customer.get('customer_name') or '').strip().casefold():
            raise HTTPException(409, 'Customer details changed; review work order first')
        docs = _read(location(request, 'doorks', 'estimates_invoices'))
        if any(isinstance(d, dict) and d.get('source_work_order_id') == work_order_id
               and d.get('source_moses_proposal_id') for d in docs):
            raise HTTPException(409, 'An AI-prepared estimate already exists for this work order; review it first')
        proposals = _read(proposal_path)
        if any(isinstance(x, dict) and x.get('kind') == 'draft_work_order_estimate'
               and x.get('record_id') == work_order_id
               and x.get('state') in ('pending', 'executing', 'needs_review') for x in proposals):
            raise HTTPException(409, 'An estimate proposal for this work order is already awaiting review')
        description = str(work_order.get('description') or work_order.get('description_of_problem') or '').strip()[:1500]
        if not description:
            raise HTTPException(409, 'Work order has no description to prepare an estimate from')
        details = {'customer_id': customer_id, 'customer': str(customer.get('name') or customer.get('customer_name'))[:200],
                   'work_order_number': str(work_order.get('job_number') or '')[:80],
                   'address': str(work_order.get('address') or '')[:500],
                   'description': description, 'notes': notes.strip(), 'pricing_required': True,
                   'estimate_number_required': True, 'status': 'Draft'}
        proposal = {'id': uuid.uuid4().hex, 'kind': 'draft_work_order_estimate',
                    'record_id': work_order_id, 'details': details,
                    'record_version': _version(work_order), 'customer_version': _version(customer),
                    'state': 'pending', 'requested_by': _actor(request), 'requested_at': _now()}
        proposals.append(proposal)
        _write(proposal_path, proposals)
        return {'proposal': proposal, 'approval_required': True, 'executed': False}


def _linked_purchase_order(rows, proposal_id):
    return next((r for r in rows if isinstance(r, dict) and r.get('source_moses_proposal_id') == proposal_id), None)


def propose_purchase_order(request, vendor_id, description, quantity, unit_cost, platform='sdc'):
    """Create an approval request for one unsent, draft workspace purchase order."""
    from decimal import Decimal, InvalidOperation
    from app.routers.workspaces import _lock, location
    _guard(request, platform)
    if not isinstance(vendor_id, str) or not 1 <= len(vendor_id) <= 80:
        raise HTTPException(422, 'Exact verified supplier ID required')
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1000:
        raise HTTPException(422, 'Description is required (max 1000 characters)')
    try:
        qty, cost = Decimal(str(quantity)), Decimal(str(unit_cost))
        if not qty.is_finite() or not cost.is_finite() or qty <= 0 or qty > 100000 or cost < 0 or cost > 10000000:
            raise ValueError()
        if len(qty.as_tuple().digits) > 15 or qty.as_tuple().exponent < -3 or cost.as_tuple().exponent < -2:
            raise ValueError()
        total = (qty * cost).quantize(Decimal('0.01'))
        if total > Decimal('100000000'): raise ValueError()
    except (InvalidOperation, ValueError, OverflowError):
        raise HTTPException(422, 'Enter valid positive quantity and nonnegative unit cost')
    with _lock:
        orders_path, proposals_path, audit_path = _paths(request, platform)
        _reconcile_locked(orders_path, proposals_path, audit_path)
        vendor = _locate(_read(location(request, platform, 'vendors')), vendor_id)
        if not vendor or not str(vendor.get('name') or '').strip():
            raise HTTPException(404, 'Supplier not found or missing name')
        if vendor.get('deactivated_at') or vendor.get('active') is False:
            raise HTTPException(409, 'Supplier is inactive')
        details = {'vendor_id': vendor_id, 'vendor': str(vendor['name'])[:200],
                   'description': description.strip(), 'quantity': str(qty),
                   'unit_cost': str(cost), 'amount': str(total)}
        proposal = {'id': uuid.uuid4().hex, 'kind': 'draft_purchase_order',
                    'record_id': vendor_id, 'details': details, 'record_version': _version(vendor),
                    'state': 'pending', 'requested_by': _actor(request), 'requested_at': _now()}
        proposals = _read(proposals_path)
        proposals.append(proposal)
        _write(proposals_path, proposals)
        return {'proposal': proposal, 'approval_required': True, 'executed': False}


def _parts_collection(platform):
    return 'inventory' if platform == 'doorks' else 'products'


def _parts_match(rows, part_number):
    needle = part_number.strip().casefold()
    return next((r for r in rows if isinstance(r, dict) and
                 str(r.get('part_number') or r.get('sku') or '').strip().casefold() == needle), None)


def _linked_part(rows, proposal_id):
    return next((r for r in rows if isinstance(r, dict)
                 and r.get('source_moses_proposal_id') == proposal_id), None)


def propose_part(request, part_number, description, manufacturer='', supplier='',
                 product_url='', image_url='', unit_cost=None, customer_price=None, platform='doorks'):
    """Create an approval request only. Input may come from inspected product pages,
    but all catalog fields must be reviewed; website text is never an instruction.
    """
    from urllib.parse import urlsplit
    from decimal import Decimal, InvalidOperation
    from app.routers.workspaces import _lock, location
    _guard(request, platform)
    fields = {'part_number':part_number,'description':description,'manufacturer':manufacturer,
              'supplier':supplier,'product_url':product_url,'image_url':image_url}
    for key, value in fields.items():
        if not isinstance(value,str) or len(value.strip()) > (1000 if key == 'description' else 500):
            raise HTTPException(422, 'Invalid part field: '+key)
        fields[key] = value.strip()
    if not 1 <= len(fields['part_number']) <= 120 or not 1 <= len(fields['description']):
        raise HTTPException(422, 'Part number and description are required')
    for key in ('product_url','image_url'):
        if fields[key] and not (key == 'image_url' and fields[key].startswith('/moses/part-image/') and chr(92) not in fields[key]) and (urlsplit(fields[key]).scheme != 'https' or not urlsplit(fields[key]).hostname
                            or urlsplit(fields[key]).username or urlsplit(fields[key]).password):
            raise HTTPException(422, 'Use a public HTTPS link for '+key)
    for key, value in (('unit_cost',unit_cost),('customer_price',customer_price)):
        if value is None or value == '':
            continue
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or amount < 0 or amount > 10000000 or amount.as_tuple().exponent < -2:
                raise ValueError()
        except (InvalidOperation, ValueError, OverflowError):
            raise HTTPException(422, 'Invalid '+key)
        fields[key] = str(amount)
    if 'unit_cost' in fields:
        fields['supplier_rate'] = fields['unit_cost']
    with _lock:
        orders_path, proposals_path, audit_path = _paths(request,platform)
        _reconcile_locked(orders_path, proposals_path, audit_path)
        catalog_path = location(request,platform,_parts_collection(platform))
        if _parts_match(_read(catalog_path),fields['part_number']):
            raise HTTPException(409, 'Part number already exists in this workspace')
        proposals = _read(proposals_path)
        if any(p.get('kind')=='create_catalog_part' and p.get('state') in ('pending','executing','needs_review')
               and str(p.get('details',{}).get('part_number','')).casefold()==fields['part_number'].casefold()
               for p in proposals if isinstance(p,dict)):
            raise HTTPException(409, 'Part creation already awaits review')
        proposal = {'id':uuid.uuid4().hex,'kind':'create_catalog_part','record_id':fields['part_number'],
                    'details':fields,'state':'pending','requested_by':_actor(request),'requested_at':_now()}
        proposals.append(proposal)
        _write(proposals_path,proposals)
        return {'proposal':proposal,'approval_required':True,'executed':False}


def _linked_invoice(documents, estimate_id):
    return next((r for r in documents if isinstance(r, dict)
                 and str(r.get('document_type', '')).casefold() == 'invoice'
                 and r.get('source_estimate_id') == estimate_id), None)


def _record_audit(audit_path, proposal):
    audit = _read(audit_path)
    if not any(isinstance(item, dict) and item.get('proposal_id') == proposal['id'] for item in audit):
        audit.append({'proposal_id': proposal['id'], 'kind': proposal['kind'],
                      'record_id': proposal['record_id'], 'old_status': proposal.get('old_status'),
                      'new_status': proposal.get('new_status'),
                      'old_schedule': proposal.get('old_schedule'),
                      'invoice_id': proposal.get('invoice_id'),
                      'invoice_number': proposal.get('invoice_number'),
                      'po_id': proposal.get('po_id'), 'po_number': proposal.get('po_number'),
                      'estimate_id': proposal.get('estimate_id'),
                      'part_id': proposal.get('part_id'),
                      'new_schedule': proposal.get('new_schedule'), 'decision': proposal['state'],
                      'actor': proposal.get('decided_by'), 'at': proposal.get('decided_at')})
        _write(audit_path, audit)


def _reconcile_locked(orders_path, proposals_path, audit_path):
    """Resolve interrupted writes without overwriting a newer business record.

    Each executing proposal contains the exact expected post-write record hash.
    If neither original nor expected result matches, mark it for manual review.
    """
    proposals = _read(proposals_path)
    orders = _read(orders_path)
    changed = False
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get('state') != 'executing':
            continue
        if proposal.get('kind') == 'draft_doorks_work_order':
            wo = _linked_work_order(_read(orders_path), proposal['id'])
            customer = _locate(_read(orders_path.parent / 'customers.json'), proposal['record_id'])
            if wo:
                proposal.update(state='executed', recovered_at=_now(),
                                work_order_id=wo['id'], job_number=wo.get('job_number', ''))
                _record_audit(audit_path, proposal)
            elif customer and _version(customer) == proposal.get('record_version'):
                proposal.update(state='pending', recovered_at=_now())
            else:
                proposal.update(state='needs_review', recovered_at=_now())
            changed = True
            continue
        if proposal.get('kind') == 'draft_work_order_estimate':
            documents = _read(orders_path.parent / 'estimates_invoices.json')
            draft = _linked_estimate(documents, proposal['id'])
            source = _locate(_read(orders_path), proposal['record_id'])
            customer = _locate(_read(orders_path.parent / 'customers.json'), proposal.get('details', {}).get('customer_id'))
            if draft:
                proposal.update(state='executed', recovered_at=_now(), estimate_id=draft['id'])
                _record_audit(audit_path, proposal)
            elif source and customer and _version(source) == proposal.get('record_version') and _version(customer) == proposal.get('customer_version'):
                proposal.update(state='pending', recovered_at=_now())
            else:
                proposal.update(state='needs_review', recovered_at=_now())
            changed = True
            continue
        if proposal.get('kind') == 'create_catalog_part':
            kind = _parts_collection('doorks' if orders_path.name == 'work_orders.json' else 'sdc')
            catalog = _read(orders_path.parent / (kind+'.json'))
            part = _linked_part(catalog, proposal['id'])
            if part:
                proposal.update(state='executed', recovered_at=_now(),part_id=part['id'])
                _record_audit(audit_path,proposal)
            elif _parts_match(catalog,proposal['details']['part_number']):
                proposal.update(state='needs_review',recovered_at=_now())
            else:
                proposal.update(state='pending',recovered_at=_now())
            changed=True
            continue
        if proposal.get('kind') == 'draft_purchase_order':
            from app.routers.workspaces import location
            po = _linked_purchase_order(_read(orders_path.parent / 'purchase_orders.json'), proposal['id'])
            vendor = _locate(_read(orders_path.parent / 'vendors.json'), proposal['record_id'])
            if po:
                proposal.update(state='executed', recovered_at=_now(),
                                po_id=po['id'], po_number=po.get('po_number', ''))
                _record_audit(audit_path, proposal)
            elif vendor and _version(vendor) == proposal.get('record_version'):
                proposal.update(state='pending', recovered_at=_now())
            else:
                proposal.update(state='needs_review', recovered_at=_now())
            changed = True
            continue
        if proposal.get('kind') == 'estimate_to_draft_invoice':
            # Source estimate and invoice live in the same workspace as the
            # proposal; derive documents path from existing order location.
            documents_path = orders_path.parent / 'estimates_invoices.json'
            docs = _read(documents_path)
            invoice = _linked_invoice(docs, proposal['record_id'])
            source = _locate(docs, proposal['record_id'])
            if invoice:
                proposal.update(state='executed', recovered_at=_now(),
                                invoice_id=invoice['id'], invoice_number=invoice.get('document_number', ''))
                _record_audit(audit_path, proposal)
            elif source and _version(source) == proposal.get('record_version'):
                proposal.update(state='pending', recovered_at=_now())
            else:
                proposal.update(state='needs_review', recovered_at=_now())
            changed = True
            continue
        order = _locate(orders, proposal['record_id'])
        current = _version(order) if order else None
        if current == proposal.get('target_version'):
            proposal['state'] = 'executed'
            proposal['recovered_at'] = _now()
            _record_audit(audit_path, proposal)
        elif current == proposal.get('record_version'):
            # This attempt did not write the business record. It remains pending
            # and can be explicitly approved again, never silently auto-executed.
            proposal['state'] = 'pending'
            proposal['recovered_at'] = _now()
        else:
            proposal['state'] = 'needs_review'
            proposal['recovered_at'] = _now()
        changed = True
    if changed:
        _write(proposals_path, proposals)
    # Also repair a missing audit event if a crash happened after finalization.
    for proposal in proposals:
        if isinstance(proposal, dict) and proposal.get('state') in ('executed', 'rejected'):
            _record_audit(audit_path, proposal)
    return proposals


def recover(request, platform='sdc'):
    """Admin-only reconciliation summary; never changes an SDC order."""
    _guard(request, platform)
    from app.routers.workspaces import _lock
    with _lock:
        proposals = _reconcile_locked(*_paths(request, platform))
        counts = {state: sum(1 for p in proposals if p.get('state') == state)
                  for state in ('pending', 'executing', 'executed', 'rejected', 'needs_review')}
        return {'states': counts, 'needs_review_ids': [p['id'] for p in proposals
                                                       if p.get('state') == 'needs_review'],
                'orders_modified': False}


def pending(request, platform='sdc'):
    """Read-only approval queue; reconciles interrupted actions first."""
    _guard(request, platform)
    from app.routers.workspaces import _lock
    with _lock:
        proposals = _reconcile_locked(*_paths(request, platform))
        waiting = [p for p in proposals if isinstance(p, dict) and p.get('state') in ('pending', 'needs_review')]
        return {'proposals': [{key: p.get(key) for key in (
            'id', 'kind', 'record_id', 'estimate_number', 'details', 'old_status', 'new_status', 'old_schedule', 'new_schedule', 'state',
            'requested_by', 'requested_at')} for p in waiting[-50:]],
            'count': len(waiting), 'limited_to': 50}


def propose(request, record_id, new_status, platform='sdc'):
    _guard(request, platform)
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 80:
        raise HTTPException(422, 'Valid record ID required')
    if new_status not in (DOORKS_STATUSES if platform == 'doorks' else STATUSES):
        raise HTTPException(422, 'Unsupported order status')
    from app.routers.workspaces import _lock
    with _lock:
        orders_path, proposals_path, audit_path = _paths(request, platform)
        _reconcile_locked(orders_path, proposals_path, audit_path)
        order = _locate(_read(orders_path), record_id)
        if order is None:
            raise HTTPException(404, 'Record not found')
        if order.get('status') == new_status:
            raise HTTPException(409, 'Record already has this status')
        proposal = {'id': uuid.uuid4().hex, 'kind': 'doorks_work_order_status' if platform == 'doorks' else 'sdc_order_status', 'record_id': record_id,
                    'old_status': order.get('status'), 'new_status': new_status,
                    'record_version': _version(order), 'state': 'pending',
                    'requested_by': _actor(request), 'requested_at': _now()}
        proposals = _read(proposals_path)
        proposals.append(proposal)
        _write(proposals_path, proposals)
        return {'proposal': proposal, 'executed': False, 'approval_required': True}


def decide(request, proposal_id, approve, platform='sdc'):
    _guard(request, platform)
    if not isinstance(approve, bool):
        raise HTTPException(422, 'Approval must be boolean')
    if not isinstance(proposal_id, str) or len(proposal_id) != 32 or any(c not in '0123456789abcdef' for c in proposal_id):
        raise HTTPException(422, 'Invalid proposal ID')
    from app.routers.workspaces import _lock
    with _lock:
        orders_path, proposals_path, audit_path = _paths(request, platform)
        proposals = _reconcile_locked(orders_path, proposals_path, audit_path)
        proposal = next((p for p in proposals if p.get('id') == proposal_id), None)
        if proposal is None:
            raise HTTPException(404, 'Proposal not found')
        if proposal.get('state') != 'pending':
            raise HTTPException(409, 'Proposal already decided or needs manual review')
        if proposal.get('kind') == 'create_catalog_part':
            from app.routers.workspaces import create, Record, location
            kind = _parts_collection(platform)
            catalog_path = location(request,platform,kind)
            if approve and _parts_match(_read(catalog_path),proposal['details']['part_number']):
                raise HTTPException(409,'Part number already exists; review before approving')
            actor,when=_actor(request),_now()
            if not approve:
                proposal.update(state='rejected',decided_by=actor,decided_at=when)
                _write(proposals_path,proposals)
                _record_audit(audit_path,proposal)
                return {'proposal_id':proposal_id,'state':'rejected','executed':False}
            proposal.update(state='executing',decided_by=actor,decided_at=when)
            _write(proposals_path,proposals)
            result=create(platform,kind,Record(data={**proposal['details'],
                'source_moses_proposal_id':proposal_id}),request)
            part=_linked_part(_read(catalog_path),proposal_id)
            if not part or part['id']!=result['item']['id']:
                raise HTTPException(500,'Part confirmation failed; recover before retrying')
            proposal.update(state='executed',part_id=part['id'])
            _write(proposals_path,proposals)
            _record_audit(audit_path,proposal)
            return {'proposal_id':proposal_id,'state':'executed','executed':True,
                    'part_id':part['id'],'part_number':part['part_number'],'sent':False}
        if proposal.get('kind') == 'draft_doorks_work_order':
            if platform != 'doorks':
                raise HTTPException(403, 'Wrong workspace for work order')
            from app.routers.workspaces import location, create, Record
            customer = _locate(_read(location(request, 'doorks', 'customers')), proposal['record_id'])
            if approve and (customer is None or _version(customer) != proposal['record_version']):
                raise HTTPException(409, 'Customer changed; review and propose again')
            actor, when = _actor(request), _now()
            if not approve:
                proposal.update(state='rejected', decided_by=actor, decided_at=when)
                _write(proposals_path, proposals)
                _record_audit(audit_path, proposal)
                return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False}
            proposal.update(state='executing', decided_by=actor, decided_at=when)
            _write(proposals_path, proposals)
            fields = {**proposal['details'], 'source_moses_proposal_id': proposal_id}
            result = create('doorks', 'work_orders', Record(data=fields), request)
            confirmed = _linked_work_order(_read(orders_path), proposal_id)
            if not confirmed or confirmed.get('id') != result['item'].get('id') or confirmed.get('status') != 'Dispatch':
                raise HTTPException(500, 'Work order confirmation failed; recover before retrying')
            proposal.update(state='executed', work_order_id=confirmed['id'],
                            job_number=confirmed.get('job_number', ''))
            _write(proposals_path, proposals)
            _record_audit(audit_path, proposal)
            return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                    'work_order_id': confirmed['id'], 'job_number': confirmed.get('job_number', ''),
                    'confirmed_status': 'Dispatch'}
        if proposal.get('kind') == 'draft_work_order_estimate':
            if platform != 'doorks':
                raise HTTPException(403, 'Wrong workspace for estimate')
            from app.routers.workspaces import location, create, Record
            source = _locate(_read(orders_path), proposal['record_id'])
            customer = _locate(_read(location(request, 'doorks', 'customers')), proposal['details']['customer_id'])
            if approve and (not source or not customer or _version(source) != proposal['record_version']
                            or _version(customer) != proposal['customer_version']):
                raise HTTPException(409, 'Work order or customer changed; review and propose again')
            actor, when = _actor(request), _now()
            if not approve:
                proposal.update(state='rejected', decided_by=actor, decided_at=when)
                _write(proposals_path, proposals)
                _record_audit(audit_path, proposal)
                return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False}
            proposal.update(state='executing', decided_by=actor, decided_at=when)
            _write(proposals_path, proposals)
            details = proposal['details']
            # No official estimate number and no pretend priced line items.
            fields = {'document_type': 'Estimate', 'document_number': '', 'status': 'Draft',
                      'customer_id': details['customer_id'], 'customer': details['customer'],
                      'work_order_number': details['work_order_number'], 'address': details['address'],
                      'description': details['description'], 'notes': details['notes'],
                      'amount': 0, 'line_items': '[]', 'source_work_order_id': proposal['record_id'],
                      'source_moses_proposal_id': proposal_id, 'requires_pricing_review': True,
                      'requires_number_assignment': True}
            result = create('doorks', 'estimates_invoices', Record(data=fields), request)
            documents_path = location(request, 'doorks', 'estimates_invoices')
            confirmed = _linked_estimate(_read(documents_path), proposal_id)
            if not confirmed or confirmed.get('id') != result['item'].get('id') or confirmed.get('status') != 'Draft':
                raise HTTPException(500, 'Estimate confirmation failed; recover before retrying')
            proposal.update(state='executed', estimate_id=confirmed['id'])
            _write(proposals_path, proposals)
            _record_audit(audit_path, proposal)
            return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                    'estimate_id': confirmed['id'], 'document_status': 'Draft', 'sent': False,
                    'pricing_required': True, 'number_required': True}
        if proposal.get('kind') == 'draft_purchase_order':
            from app.routers.workspaces import location, create, Record
            vendor = _locate(_read(location(request, platform, 'vendors')), proposal['record_id'])
            if approve and (vendor is None or _version(vendor) != proposal['record_version']):
                raise HTTPException(409, 'Supplier changed; review and propose again')
            actor, when = _actor(request), _now()
            if not approve:
                proposal.update(state='rejected', decided_by=actor, decided_at=when)
                _write(proposals_path, proposals)
                _record_audit(audit_path, proposal)
                return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False}
            proposal.update(state='executing', decided_by=actor, decided_at=when)
            _write(proposals_path, proposals)
            # Reuse the regular workspace endpoint for server-managed PO numbers.
            fields = {**proposal['details'], 'status': 'Draft',
                      'source_moses_proposal_id': proposal_id}
            result = create(platform, 'purchase_orders', Record(data=fields), request)
            po = _linked_purchase_order(_read(location(request, platform, 'purchase_orders')), proposal_id)
            if po is None or po.get('id') != result['item'].get('id') or po.get('status') != 'Draft':
                raise HTTPException(500, 'PO confirmation failed; reconcile before retrying')
            proposal.update(state='executed', po_id=po['id'], po_number=po['po_number'])
            _write(proposals_path, proposals)
            _record_audit(audit_path, proposal)
            return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                    'po_id': po['id'], 'po_number': po['po_number'], 'document_status': 'Draft',
                    'sent': False}
        if proposal.get('kind') == 'estimate_to_draft_invoice':
            from app.routers.workspaces import location, convert_estimate_to_invoice
            documents_path = location(request, platform, 'estimates_invoices')
            docs = _read(documents_path)
            source = _locate(docs, proposal['record_id'])
            if approve and (source is None or _version(source) != proposal['record_version']
                            or _linked_invoice(docs, proposal['record_id'])):
                raise HTTPException(409, 'Estimate changed or invoice exists; review before retrying')
            actor, when = _actor(request), _now()
            if not approve:
                proposal.update(state='rejected', decided_by=actor, decided_at=when)
                _write(proposals_path, proposals)
                _record_audit(audit_path, proposal)
                return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False,
                        'record_id': proposal['record_id']}
            proposal.update(state='executing', decided_by=actor, decided_at=when)
            _write(proposals_path, proposals)
            # Existing converter owns invoice sequences, linking and duplicate prevention.
            result = convert_estimate_to_invoice(platform, proposal['record_id'], request)
            invoice = result['item']
            confirmed = _linked_invoice(_read(documents_path), proposal['record_id'])
            if not confirmed or confirmed.get('id') != invoice.get('id') or confirmed.get('status') != 'Draft':
                raise HTTPException(500, 'Invoice confirmation failed; recover before retrying')
            proposal.update(state='executed', invoice_id=confirmed['id'],
                            invoice_number=confirmed.get('document_number', ''))
            _write(proposals_path, proposals)
            _record_audit(audit_path, proposal)
            return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                    'record_id': proposal['record_id'], 'invoice_id': confirmed['id'],
                    'invoice_number': confirmed.get('document_number', ''),
                    'document_status': 'Draft', 'sent': False}
        orders = _read(orders_path)
        order = _locate(orders, proposal['record_id'])
        if approve and (order is None or _version(order) != proposal['record_version']):
            raise HTTPException(409, 'Record changed since proposal; review and propose again')
        actor, when = _actor(request), _now()
        if approve and proposal.get('kind') == 'doorks_work_order_schedule':
            _assert_schedule_safe(request, order)
        if approve:
            # Persist execution intent *before* changing the order. This makes
            # an interrupted operation detectable on subsequent calls.
            target = {**order, 'updated_at': when}
            if proposal.get('kind') == 'doorks_work_order_schedule':
                target.update(proposal['new_schedule'])
            else:
                target['status'] = proposal['new_status']
            proposal.update(state='executing', decided_by=actor, decided_at=when,
                            target_version=_version(target))
            _write(proposals_path, proposals)
            order.clear()
            order.update(target)
            _write(orders_path, orders)
        proposal.update(state='executed' if approve else 'rejected', decided_by=actor, decided_at=when)
        # For a rejection, persist the decision BEFORE the audit so a failed
        # audit cannot leave an apparently pending, approvable proposal.
        if not approve:
            _write(proposals_path, proposals)
        _record_audit(audit_path, proposal)
        if approve:
            _write(proposals_path, proposals)
        confirmed = _locate(_read(orders_path), proposal['record_id'])
        if approve and (confirmed is None or _version(confirmed) != proposal['target_version']):
            raise HTTPException(500, 'Order confirmation failed; reconcile before retrying')
        return {'proposal_id': proposal_id, 'state': proposal['state'], 'executed': approve,
                'record_id': proposal['record_id'],
                'confirmed_status': confirmed.get('status') if confirmed else None,
                'confirmed_schedule': {k: confirmed.get(k, '') for k in ('scheduled_date', 'scheduled_time')}
                if confirmed and proposal.get('kind') == 'doorks_work_order_schedule' else None}
