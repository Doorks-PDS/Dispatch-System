"""Approval-controlled PDS parts creation using the existing /data/parts catalog.

Independent PDS proposal file; uncertain writes never replay automatically.
"""
from __future__ import annotations
import os
import re
import uuid
from pathlib import Path
from threading import RLock
from fastapi import HTTPException
from app.services.moses_pds_actions import _actor, _stamp, _read, _save

_lock = RLock()


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in required')
    if request.session.get('active_platform') != 'pds' or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'PDS office-admin required')
    if os.getenv('DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED', '').strip().lower() != 'true':
        raise HTTPException(503, 'PDS Moses parts actions disabled')


def _path(request):
    p = Path(request.app.state.data_dir) / 'moses_pds' / 'part_proposals.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _catalog(request):
    from app.routers import data
    saved = data._read_json_file(data._parts_path(request), {'items': []})
    return saved.get('items', []) if isinstance(saved, dict) else []


def _match(items, number):
    key = number.strip().casefold()
    return next((p for p in items if isinstance(p, dict) and
                 str(p.get('part_number') or p.get('Item') or '').strip().casefold() == key), None)


def _review_interrupted(rows):
    changed = False
    for p in rows:
        if p.get('state') == 'executing':
            # An interrupted write is ambiguous. Never manufacture another part.
            p['state'] = 'needs_review'
            p['recovered_at'] = _stamp()
            changed = True
    return changed


def propose(request, part_number, description, manufacturer='', supplier='', product_url='', image_url='', customer_price=None):
    _guard(request)
    from app.routers.data import _part_https_url
    fields = dict(part_number=part_number, description=description, manufacturer=manufacturer,
                  supplier=supplier, product_url=product_url, image_url=image_url)
    if any(not isinstance(v, str) or len(v) > (1000 if k == 'description' else 1500) for k, v in fields.items()):
        raise HTTPException(422, 'Invalid part fields')
    fields = {k: v.strip() for k, v in fields.items()}
    if not fields['part_number'] or len(fields['part_number']) > 120 or not fields['description']:
        raise HTTPException(422, 'Part number and description required')
    if fields['product_url']:
        _part_https_url(fields['product_url'])
    if fields['image_url'] and not fields['image_url'].startswith('/moses/part-image/pds/'):
        _part_https_url(fields['image_url'])
    if fields['image_url'].startswith('/moses/part-image/pds/'):
        from app.routers.moses import get_pds_part_image
        filename = fields['image_url'].rsplit('/', 1)[-1]
        get_pds_part_image(filename, request)  # check ownership and existence
    if customer_price is not None:
        if isinstance(customer_price, bool) or not isinstance(customer_price, (float, int)) or not 0 <= customer_price <= 10000000:
            raise HTTPException(422, 'Invalid customer price')
    fields['price'] = customer_price if customer_price is not None else ''
    with _lock:
        path = _path(request)
        rows = _read(path)
        if _review_interrupted(rows):
            _save(path, rows)
        if _match(_catalog(request), fields['part_number']):
            raise HTTPException(409, 'Part number already exists in PDS')
        if any(p.get('state') in ('pending', 'needs_review', 'executing') and
               str(p.get('details', {}).get('part_number', '')).casefold() == fields['part_number'].casefold()
               for p in rows):
            raise HTTPException(409, 'A proposal for this part already exists')
        p = dict(id=uuid.uuid4().hex, kind='pds_create_catalog_part', record_id=fields['part_number'],
                 details=fields, state='pending', requested_by=_actor(request), requested_at=_stamp())
        rows.append(p)
        _save(path, rows)
        return {'proposal': p, 'approval_required': True, 'executed': False}


def pending(request):
    _guard(request)
    with _lock:
        path = _path(request)
        rows = _read(path)
        if _review_interrupted(rows):
            _save(path, rows)
        waiting = [p for p in rows if p.get('state') in ('pending', 'needs_review')]
        return {'proposals': [{k: p.get(k) for k in ('id', 'kind', 'record_id', 'details', 'state',
                              'requested_by', 'requested_at')} for p in waiting[-50:]], 'count': len(waiting)}


def has(request, proposal_id):
    with _lock:
        return any(p.get('id') == proposal_id for p in _read(_path(request)))


def decide(request, proposal_id, approve):
    _guard(request)
    if not isinstance(approve, bool) or not isinstance(proposal_id, str) or not re.fullmatch('[a-f0-9]{32}', proposal_id):
        raise HTTPException(422, 'Invalid decision')
    with _lock:
        path = _path(request)
        rows = _read(path)
        if _review_interrupted(rows):
            _save(path, rows)
        p = next((item for item in rows if item.get('id') == proposal_id), None)
        if not p:
            raise HTTPException(404, 'Part proposal not found')
        if p['state'] != 'pending':
            raise HTTPException(409, 'Part proposal already decided or needs review')
        p['decided_by'], p['decided_at'] = _actor(request), _stamp()
        if not approve:
            p['state'] = 'rejected'
            _save(path, rows)
            return {'proposal_id': proposal_id, 'state': 'rejected', 'executed': False}
        if _match(_catalog(request), p['details']['part_number']):
            raise HTTPException(409, 'PDS part already exists; review duplicate before approval')
        p['state'] = 'executing'
        _save(path, rows)
        try:
            from app.routers import data
            record = data.create_part(request, data.PartPayload(**p['details']), None)['item']
            verified = next((row for row in _catalog(request) if row.get('id') == record['id']), None)
            if not verified or verified.get('part_number') != p['details']['part_number']:
                raise RuntimeError('PDS part save could not be confirmed')
        except Exception as exc:
            p['state'] = 'needs_review'
            _save(path, rows)
            raise HTTPException(500, 'PDS part creation needs manual review; do not repeat approval') from exc
        p['state'], p['part_id'], p['confirmed_at'] = 'executed', record['id'], _stamp()
        _save(path, rows)
        return {'proposal_id': proposal_id, 'state': 'executed', 'executed': True,
                'part_id': record['id'], 'part_number': record['part_number'], 'sent': False}
