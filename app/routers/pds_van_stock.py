"""PDS van inventory, tied to the existing PDS Parts List and inventory ledger.

All writes are serialized by the same flock used by /data/parts/*/adjust-stock.
The van ledger is authoritative for van counts and warehouse transfers; no automatic
part creation, payroll adjustments, purchases, or notification sends occur here.
"""
from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/pds-van-stock', tags=['pds-van-stock'])


def _guard(request: Request, *, write: bool = False):
    user = getattr(request.state, 'auth_user', None)
    role = getattr(request.state, 'auth_role', None)
    if not isinstance(user, dict) or role not in ('office', 'office_admin', 'tech', 'lead'):
        raise HTTPException(401, 'Sign in to PDS')
    if request.session.get('active_platform') != 'pds':
        raise HTTPException(403, 'Switch to PDS workspace')
    if write and role not in ('office', 'office_admin'):
        raise HTTPException(403, 'PDS office authorization required')
    return str(user.get('name') or user.get('id') or 'office')[:120]


def _path(request: Request) -> Path:
    root = getattr(request.app.state, 'data_dir', None)
    if not root:
        raise HTTPException(503, 'Durable data directory not configured')
    return Path(root) / 'pds_van_stock.json'


def _initial() -> dict:
    return {'version': 1, 'template': {}, 'vans': {}, 'events': []}


def _read(path: Path) -> dict:
    if not path.exists():
        return _initial()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not all(isinstance(data.get(k), t) for k, t in [('template', dict), ('vans', dict), ('events', list)]):
            raise ValueError('invalid stock data')
        if len(data['events']) > 200000:
            raise ValueError('ledger too large to load')
        return data
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'Van stock records require review; changes disabled') from exc


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def _locked(request: Request):
    # Same cross-worker lock as data.adjust_pds_part_stock; prevents overdraw.
    lock_path = Path(request.app.state.data_dir) / 'pds_parts_stock_events.json.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _parts(request: Request) -> dict:
    # Do not use the generic catalog reader here: it replaces malformed JSON
    # with an empty list, hiding damaged production part records. Van stock
    # transfers must fail closed until an operator reviews the catalog.
    from app.routers.data import _parts_path
    path = _parts_path(request)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict) or not isinstance(raw.get('items'), list):
            raise ValueError('Invalid parts catalog shape')
        if any(not isinstance(p, dict) or not p.get('id') for p in raw['items']):
            raise ValueError('Invalid parts catalog entry')
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'PDS Parts List requires review; van stock changes disabled') from exc
    return {str(p['id']): p for p in raw['items']}


def _people(request: Request) -> dict:
    """Eligible active staff only; historical van ledgers remain untouched."""
    store = request.app.state.employees_store
    employees = {str(e['id']): dict(e) for e in store.list()
                 if isinstance(e, dict) and e.get('id') and
                 str(e.get('status', 'Active')).lower() == 'active' and e.get('active') is not False}
    users_store = getattr(request.app.state, 'users_store', None)
    if users_store:
        by_name = {str(e.get('name', '')).strip().lower(): key for key, e in employees.items()}
        for user in users_store.list_users():
            if not isinstance(user, dict) or not user.get('id'):
                continue
            name = str(user.get('name') or user.get('username') or '').strip()
            if not name:
                continue
            existing_id = by_name.get(name.lower())
            if not user.get('active', True):
                if existing_id:
                    employees.pop(existing_id, None)
                continue
            if existing_id:
                employees[existing_id]['role'] = user.get('role') or employees[existing_id].get('role', 'tech')
            else:
                employees[str(user['id'])] = {'id': str(user['id']), 'name': name, 'role': user.get('role', 'tech')}
    return employees


def _balances(data: dict):
    vans = {}
    moved = {}
    for event in data['events']:
        try:
            van = str(event['employee_id']); part = str(event['part_id'])
            delta = int(event['delta']); warehouse_delta = int(event['warehouse_delta'])
            if not van or not part or isinstance(event['delta'], bool) or isinstance(event['warehouse_delta'], bool):
                raise ValueError()
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(503, 'Van stock ledger requires review') from exc
        key = (van, part)
        vans[key] = vans.get(key, 0) + delta
        moved[part] = moved.get(part, 0) + warehouse_delta
        if vans[key] < 0:
            raise HTTPException(503, 'Van stock ledger contains a negative count')
    return vans, moved


def warehouse_transfer_deltas(request: Request):
    """Deltas applied to existing warehouse stock calculation, without touching its ledger."""
    return _balances(_read(_path(request)))[1]


def _low(quantity: int, minimum: Optional[int]):
    # Empty minimum is intentionally not treated as zero or an alert.
    return minimum is not None and quantity < minimum


def _view(request: Request):
    from app.routers.data import _pds_stock_balances
    data = _read(_path(request))
    parts = _parts(request)
    people = _people(request)
    van_balances, _ = _balances(data)
    warehouse = _pds_stock_balances(request)
    rows = []
    for employee_id, config in sorted(data['vans'].items(), key=lambda x: str(x[1].get('employee_name', '')).lower()):
        employee = people.get(employee_id, {})
        items = []
        for part_id, settings in config.get('items', {}).items():
            part = parts.get(part_id, {})
            count = van_balances.get((employee_id, part_id), 0)
            minimum = settings.get('minimum')
            target = settings.get('target')
            items.append({'part_id': part_id, 'part_number': part.get('part_number', ''), 'description': part.get('description', ''),
                          'quantity': count, 'minimum': minimum, 'target': target,
                          'image_url': part.get('image_url', ''), 'product_url': part.get('product_url', ''),
                          'manufacturer': part.get('manufacturer', part.get('Manufacturer', '')),
                          'low': _low(count, minimum), 'needed': max(0, (target if target is not None else minimum or 0) - count) if _low(count, minimum) else 0,
                          'catalog_missing': not bool(part)})
        rows.append({'employee_id': employee_id, 'employee_name': employee.get('name') or config.get('employee_name') or 'Unknown employee',
                     'enabled': bool(config.get('enabled', True)), 'items': items,
                     'low_count': sum(1 for i in items if i['low'])})
    catalog = []
    for part_id, part in parts.items():
        threshold = part.get('min_stock')
        if threshold == '': threshold = None
        recorded = part_id in warehouse
        count = warehouse.get(part_id)
        catalog.append({'id': part_id, 'part_number': part.get('part_number', ''), 'description': part.get('description', ''),
                        'warehouse': count, 'stock_recorded': recorded, 'minimum': threshold,
                        'image_url': part.get('image_url', ''), 'product_url': part.get('product_url', ''),
                        'manufacturer': part.get('manufacturer', part.get('Manufacturer', '')),
                        'low': recorded and _low(count, threshold), 'needed': max(0, threshold-count) if recorded and _low(count, threshold) else 0})
    return {'ok': True, 'vans': rows, 'template': data['template'], 'catalog': catalog,
            'alerts': {'vans': sum(v['low_count'] for v in rows if v['enabled']), 'warehouse': sum(1 for c in catalog if c['low'])}}


@router.get('')
def overview(request: Request):
    _guard(request)
    return _view(request)


class VanSetup(BaseModel):
    employee_id: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    use_template: bool = True


@router.post('/vans')
def set_up_van(payload: VanSetup, request: Request):
    _guard(request, write=True)
    person = _people(request).get(payload.employee_id)
    if not person:
        raise HTTPException(404, 'Employee not found')
    if str(person.get('role', 'tech')).lower() not in ('tech', 'lead', 'technician'):
        raise HTTPException(400, 'Van stock belongs to technicians and leads')
    with _locked(request):
        path = _path(request); data = _read(path)
        row = data['vans'].get(payload.employee_id)
        if row:
            row['enabled'] = payload.enabled
        else:
            row = {'employee_name': person.get('name', ''), 'enabled': payload.enabled,
                   'items': dict(data['template']) if payload.use_template else {}}
            data['vans'][payload.employee_id] = row
        _write(path, data)
    return _view(request)


class Threshold(BaseModel):
    part_id: str = Field(min_length=1, max_length=120)
    minimum: Optional[int] = Field(default=None, ge=0, le=100000)
    target: Optional[int] = Field(default=None, ge=0, le=100000)


@router.put('/template')
def template_item(payload: Threshold, request: Request):
    _guard(request, write=True)
    if payload.part_id not in _parts(request):
        raise HTTPException(404, 'Part not in PDS Parts List')
    if payload.minimum is not None and payload.target is not None and payload.target < payload.minimum:
        raise HTTPException(422, 'Target must be at least minimum')
    with _locked(request):
        path = _path(request); data = _read(path)
        data['template'][payload.part_id] = {'minimum': payload.minimum, 'target': payload.target}
        # Applying a template adds missing items, never overwrites van-specific levels.
        for van in data['vans'].values():
            van['items'].setdefault(payload.part_id, dict(data['template'][payload.part_id]))
        _write(path, data)
    return _view(request)


@router.put('/vans/{employee_id}/items')
def van_item(employee_id: str, payload: Threshold, request: Request):
    _guard(request, write=True)
    if payload.part_id not in _parts(request):
        raise HTTPException(404, 'Part not in PDS Parts List')
    if payload.minimum is not None and payload.target is not None and payload.target < payload.minimum:
        raise HTTPException(422, 'Target must be at least minimum')
    with _locked(request):
        path = _path(request); data = _read(path)
        if employee_id not in data['vans']:
            raise HTTPException(404, 'Set up this employee van first')
        data['vans'][employee_id]['items'][payload.part_id] = {'minimum': payload.minimum, 'target': payload.target}
        _write(path, data)
    return _view(request)


class Movement(BaseModel):
    employee_id: str = Field(min_length=1, max_length=120)
    part_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=0, le=100000)
    movement: Literal['load', 'return', 'used', 'count']
    reason: str = Field(min_length=3, max_length=300)
    request_id: str = Field(min_length=8, max_length=120)


@router.post('/movements')
def movement(payload: Movement, request: Request):
    actor = _guard(request, write=True)
    from app.routers.data import _pds_stock_balances
    with _locked(request):
        path = _path(request); data = _read(path)
        if payload.part_id not in _parts(request):
            raise HTTPException(404, 'Part not in PDS Parts List')
        van = data['vans'].get(payload.employee_id)
        if not van or not van.get('enabled', True):
            raise HTTPException(404, 'No active van setup')
        for event in data['events']:
            if event.get('request_id') == payload.request_id:
                if any(event.get(k) != getattr(payload, k) for k in ('employee_id', 'part_id', 'quantity', 'movement', 'reason')):
                    raise HTTPException(409, 'Request ID already used for a different movement')
                return {'ok': True, 'duplicate': True, 'event_id': event['id']}
        van_balance, _ = _balances(data)
        existing = van_balance.get((payload.employee_id, payload.part_id), 0)
        warehouse = _pds_stock_balances(request)
        if payload.quantity == 0 and payload.movement != 'count':
            raise HTTPException(422, 'A stock movement must be greater than zero')
        if payload.movement == 'load':
            if payload.part_id not in warehouse:
                raise HTTPException(409, 'Warehouse stock must be counted before transferring to a van')
            if warehouse[payload.part_id] < payload.quantity:
                raise HTTPException(409, 'Insufficient warehouse stock')
            delta, warehouse_delta = payload.quantity, -payload.quantity
        elif payload.movement == 'return':
            if existing < payload.quantity:
                raise HTTPException(409, 'Cannot return more than van stock')
            delta, warehouse_delta = -payload.quantity, payload.quantity
        elif payload.movement == 'used':
            if existing < payload.quantity:
                raise HTTPException(409, 'Cannot use more than van stock')
            delta, warehouse_delta = -payload.quantity, 0
        else:  # Explicit physically verified count; not a warehouse transfer.
            delta, warehouse_delta = payload.quantity - existing, 0
        event = {'id': uuid.uuid4().hex, 'request_id': payload.request_id,
                 'employee_id': payload.employee_id, 'part_id': payload.part_id,
                 'quantity': payload.quantity, 'movement': payload.movement,
                 'delta': delta, 'warehouse_delta': warehouse_delta,
                 'reason': payload.reason.strip(), 'actor': actor,
                 'created_at': datetime.now(timezone.utc).isoformat()}
        data['events'].append(event)
        van['items'].setdefault(payload.part_id, {'minimum': None, 'target': None})
        _write(path, data)
    return {'ok': True, 'duplicate': False, 'event_id': event['id'], 'van_quantity': existing + delta}


@router.get('/events')
def recent_events(request: Request, limit: int = 100):
    _guard(request)
    return {'ok': True, 'items': _read(_path(request))['events'][-max(1, min(limit, 500)):][::-1]}
