"""PDS van inventory, tied to the existing PDS Parts List and inventory ledger.

All writes are serialized by the same flock used by /data/parts/*/adjust-stock.
The van ledger is authoritative for van counts and warehouse transfers; no automatic
part creation, payroll adjustments, purchases, or notification sends occur here.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, date
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



def _actor_fields(request: Request) -> dict:
    """Stable identity on every change, without publishing credentials or emails."""
    user = getattr(request.state, 'auth_user', None) or {}
    return {'actor': str(user.get('name') or user.get('username') or user.get('id') or 'Unknown staff')[:120],
            'actor_user_id': str(user.get('id') or '')[:120],
            'actor_role': str(getattr(request.state, 'auth_role', '') or '')[:32]}


def _own_van(request: Request, employee_id: str) -> bool:
    if getattr(getattr(request, 'state', None), 'auth_role', '') not in ('tech', 'lead'):
        return False
    # Match the authenticated login through the *active* PDS scheduling
    # identity resolver. Never trust a name or employee ID supplied by the client.
    from app.routers.pds_scheduling import _current_employee_id
    user = getattr(request.state, 'auth_user', None)
    if not isinstance(user, dict):
        return False
    try:
        return str(_current_employee_id(request, user)) == str(employee_id)
    except HTTPException:
        return False


def _van_write(request: Request, employee_id: str, *, office_only: bool = False) -> str:
    actor = _guard(request)
    if getattr(request.state, 'auth_role', '') in ('office', 'office_admin'):
        return actor
    if not office_only and _own_van(request, employee_id):
        return actor
    raise HTTPException(403, 'You can update only your assigned van; office authorization required for fleet administration')


def _change(data: dict, request: Request, employee_id: str, action: str, description: str):
    event = {'id': uuid.uuid4().hex, 'employee_id': str(employee_id), 'action': action,
             'description': str(description)[:300], 'created_at': datetime.now(timezone.utc).isoformat(),
             **_actor_fields(request)}
    history = data.setdefault('change_history', [])
    history.append(event)
    if len(history) > 50000:
        raise HTTPException(409, 'Fleet change history requires archival review')
    return event


def _movement_history(data: dict, parts: dict, people: dict, *, limit: int = 100, employee_id: str | None = None) -> list[dict]:
    """Render ledger IDs as comprehensible, reconciled movement descriptions."""
    balances: dict[tuple[str, str], int] = {}
    result = []
    for event in data.get('events', []):
        van_id = str(event.get('employee_id') or '')
        part_id = str(event.get('part_id') or '')
        key = (van_id, part_id)
        before = balances.get(key, 0)
        try:
            delta = int(event.get('delta', 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(503, 'Van stock history requires review') from exc
        after = before + delta
        balances[key] = after
        if employee_id is not None and employee_id != van_id:
            continue
        part = parts.get(part_id) or {}
        number = str(part.get('part_number') or part_id)
        name = str(people.get(van_id, {}).get('name') or data.get('vans', {}).get(van_id, {}).get('employee_name') or van_id)
        other_id = str(event.get('counterparty') or '')
        other_name = str(people.get(other_id, {}).get('name') or data.get('vans', {}).get(other_id, {}).get('employee_name') or other_id)
        movement = str(event.get('movement') or '')
        qty = event.get('quantity', abs(delta))
        labels = {'load': f'Loaded {qty} × {number} into {name}’s van',
                  'return': f'Returned {qty} × {number} from {name}’s van to warehouse',
                  'used': f'Used {qty} × {number} from {name}’s van',
                  'count': f'Physically counted {number} in {name}’s van: {after} on hand',
                  'transfer_out': f'Transferred {qty} × {number} from {name} to {other_name}',
                  'transfer_in': f'Received {qty} × {number} into {name}’s van from {other_name}'}
        result.append({**event, 'employee_name': name, 'part_number': number,
                       'part_description': str(part.get('description') or ''),
                       'summary': labels.get(movement, f'{name}: {number} stock adjustment ({delta:+d})'),
                       'quantity_before': before, 'quantity_after': after,
                       'warehouse_effect': int(event.get('warehouse_delta', 0)),
                       'performed_by': str(event.get('actor') or 'Legacy record — staff not recorded')})
    return result[-max(1, min(limit, 500)):][::-1]

def _path(request: Request) -> Path:
    root = getattr(request.app.state, 'data_dir', None)
    if not root:
        raise HTTPException(503, 'Durable data directory not configured')
    return Path(root) / 'pds_van_stock.json'


def _initial() -> dict:
    return {'version': 3, 'template': {}, 'vans': {}, 'events': [], 'source_reviews': {}, 'review_history': [], 'change_history': []}


def _read(path: Path) -> dict:
    if not path.exists():
        return _initial()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not all(isinstance(data.get(k), t) for k, t in [('template', dict), ('vans', dict), ('events', list)]):
            raise ValueError('invalid stock data')
        data.setdefault('source_reviews', {})
        data.setdefault('review_history', [])
        data.setdefault('change_history', [])
        if not isinstance(data['source_reviews'], dict) or not isinstance(data['review_history'], list) or not isinstance(data['change_history'], list):
            raise ValueError('invalid source review data')
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
    office = getattr(getattr(request, 'state', None), 'auth_role', '') in ('office', 'office_admin')
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
        owner = _own_van(request, employee_id) if not office else False
        vehicle = dict(config.get('vehicle') or {}) if office or owner else {}
        if not office:  # Never expose policy information to field accounts.
            for field in ('insurance_policy', 'insurance_carrier', 'vin'):
                vehicle.pop(field, None)
        rows.append({'employee_id': employee_id, 'employee_name': employee.get('name') or config.get('employee_name') or 'Unknown employee',
                     'vehicle': vehicle,
                     'service_events': list(reversed((config.get('service_events') or [])[-50:])) if office or owner else [],
                     'can_edit': office or owner, 'can_edit_vehicle': office,
                     'recent_movements': _movement_history(data, parts, people, limit=15, employee_id=employee_id) if office or owner else [],
                     'enabled': bool(config.get('enabled', True)), 'items': items,
                     'low_count': sum(1 for i in items if i['low'])})
    van_totals = {}
    for (van_id, part_id), count in van_balances.items():
        van_totals[part_id] = van_totals.get(part_id, 0) + count
    catalog = []
    for part_id, part in parts.items():
        threshold = part.get('min_stock')
        if threshold == '': threshold = None
        recorded = part_id in warehouse
        count = warehouse.get(part_id)
        catalog.append({'id': part_id, 'part_number': part.get('part_number', ''), 'description': part.get('description', ''),
                        'warehouse': count, 'stock_recorded': recorded, 'van_total': van_totals.get(part_id, 0),
                        'total_tracked': (count if recorded else 0) + van_totals.get(part_id, 0),
                        'minimum': threshold,
                        'image_url': part.get('image_url', ''), 'product_url': part.get('product_url', ''),
                        'manufacturer': part.get('manufacturer', part.get('Manufacturer', '')),
                        'low': recorded and _low(count, threshold), 'needed': max(0, threshold-count) if recorded and _low(count, threshold) else 0})
    template_items = []
    for part_id, thresholds in data['template'].items():
        part = parts.get(part_id) or {}
        template_items.append({'part_id': part_id, 'part_number': part.get('part_number', ''),
                               'description': part.get('description', ''), 'minimum': thresholds.get('minimum'),
                               'target': thresholds.get('target'), 'catalog_missing': not bool(part)})
    pending = [e for e in data['events'] if e.get('movement') == 'count' and
               e.get('delta', 0) != 0 and
               data['source_reviews'].get(e.get('id'), {}).get('source_type') in (None, 'unknown')]
    return {'ok': True, 'vans': rows, 'template': data['template'], 'template_items': template_items,
            'catalog': catalog, 'source_review_pending': len(pending),
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
            _change(data, request, payload.employee_id, 'van_status_changed', 'Enabled van' if payload.enabled else 'Disabled van')
        else:
            row = {'employee_name': person.get('name', ''), 'enabled': payload.enabled,
                   'items': dict(data['template']) if payload.use_template else {}}
            data['vans'][payload.employee_id] = row
            _change(data, request, payload.employee_id, 'van_created', f'Created van for {person.get("name", payload.employee_id)}')
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
        _change(data, request, '', 'template_updated', f'Updated standard part {payload.part_id}: minimum {payload.minimum}, target {payload.target}')
        # Standard stock is a future-van setup template only. Existing van
        # tickets retain their individual items and quantities unchanged.
        _write(path, data)
    return _view(request)


@router.put('/vans/{employee_id}/items')
def van_item(employee_id: str, payload: Threshold, request: Request):
    _van_write(request, employee_id)
    if payload.part_id not in _parts(request):
        raise HTTPException(404, 'Part not in PDS Parts List')
    if payload.minimum is not None and payload.target is not None and payload.target < payload.minimum:
        raise HTTPException(422, 'Target must be at least minimum')
    with _locked(request):
        path = _path(request); data = _read(path)
        if employee_id not in data['vans']:
            raise HTTPException(404, 'Set up this employee van first')
        data['vans'][employee_id]['items'][payload.part_id] = {'minimum': payload.minimum, 'target': payload.target}
        _change(data, request, employee_id, 'van_item_updated', f'Updated {payload.part_id}: minimum {payload.minimum}, target {payload.target}')
        _write(path, data)
    return _view(request)


class VehicleDetails(BaseModel):
    label: str = Field(default='', max_length=120)
    year: str = Field(default='', max_length=10)
    make: str = Field(default='', max_length=70)
    model: str = Field(default='', max_length=70)
    license_plate: str = Field(default='', max_length=30)
    vin: str = Field(default='', max_length=40)
    insurance_carrier: str = Field(default='', max_length=120)
    insurance_policy: str = Field(default='', max_length=100)
    insurance_expires: str = Field(default='', max_length=30)
    registration_expires: str = Field(default='', max_length=30)
    next_service: str = Field(default='', max_length=30)
    odometer: str = Field(default='', max_length=30)
    notes: str = Field(default='', max_length=1500)


@router.put('/vans/{employee_id}/vehicle')
def save_vehicle(employee_id: str, payload: VehicleDetails, request: Request):
    actor = _guard(request, write=True)
    with _locked(request):
        path = _path(request); data = _read(path)
        van = data['vans'].get(employee_id)
        if not van:
            raise HTTPException(404, 'Van ticket does not exist')
        van['vehicle'] = {k: v.strip() for k, v in payload.model_dump().items()}
        van['vehicle_updated_by'] = actor
        _change(data, request, employee_id, 'vehicle_updated', 'Updated fleet vehicle information')
        van['vehicle_updated_at'] = datetime.now(timezone.utc).isoformat()
        _write(path, data)
    return {'ok': True, 'vehicle': van['vehicle']}



class VehicleServiceEvent(BaseModel):
    kind: Literal['service', 'repair', 'accident', 'inspection', 'note']
    date: str = Field(min_length=10, max_length=10)
    odometer: str = Field(default='', max_length=30)
    provider: str = Field(default='', max_length=120)
    notes: str = Field(min_length=2, max_length=1500)
    request_id: str = Field(default='', max_length=100)


@router.post('/vans/{employee_id}/service-events')
def record_vehicle_service(employee_id: str, payload: VehicleServiceEvent, request: Request):
    """Immutable service/incident history; owner or office may record entries."""
    actor = _van_write(request, employee_id)
    try:
        recorded_day = date.fromisoformat(payload.date).isoformat()
    except ValueError as exc:
        raise HTTPException(422, 'Enter a valid service date') from exc
    if not payload.notes.strip():
        raise HTTPException(422, 'Service or incident notes required')
    event = {'id': uuid.uuid4().hex, 'kind': payload.kind, 'date': recorded_day,
             'odometer': payload.odometer.strip(), 'provider': payload.provider.strip(),
             'notes': payload.notes.strip(), 'created_at': datetime.now(timezone.utc).isoformat(),
             'created_by': actor, 'request_id': payload.request_id.strip(), **_actor_fields(request)}
    with _locked(request):
        path = _path(request)
        data = _read(path)
        van = data['vans'].get(employee_id)
        if not van:
            raise HTTPException(404, 'Van ticket does not exist')
        events = van.setdefault('service_events', [])
        if not isinstance(events, list) or len(events) >= 1000:
            raise HTTPException(409, 'Vehicle history requires archival review')
        if event['request_id']:
            previous=next((e for e in events if e.get('request_id')==event['request_id']),None)
            if previous:
                if any(previous.get(k)!=event.get(k) for k in ('kind','date','odometer','provider','notes')):
                    raise HTTPException(409, 'Vehicle history request ID was reused with different details')
                return {'ok':True,'event':previous,'reused':True}
        events.append(event)
        _change(data, request, employee_id, 'service_recorded', f'{payload.kind.title()} on {recorded_day}: {payload.notes[:120]}')
        _write(path, data)
    return {'ok': True, 'event': event}

@router.delete('/template/{part_id}')
def remove_template_item(part_id: str, request: Request):
    _guard(request, write=True)
    with _locked(request):
        path = _path(request); data = _read(path)
        if part_id not in data['template']:
            raise HTTPException(404, 'Template item not found')
        del data['template'][part_id]
        _change(data, request, '', 'template_removed', f'Removed {part_id} from future standard template')
        _write(path, data)
    return {'ok': True, 'removed': part_id, 'existing_vans_unchanged': True}


@router.delete('/vans/{employee_id}/items/{part_id}')
def remove_van_item(employee_id: str, part_id: str, request: Request):
    _van_write(request, employee_id)
    with _locked(request):
        path = _path(request); data = _read(path)
        van = data['vans'].get(employee_id)
        if not van or part_id not in van.get('items', {}):
            raise HTTPException(404, 'Van part not found')
        balances, _ = _balances(data)
        if balances.get((employee_id, part_id), 0) != 0:
            raise HTTPException(409, 'Move or reconcile existing stock before removing this part')
        del van['items'][part_id]
        _change(data, request, employee_id, 'van_item_removed', f'Removed {part_id} from van setup (zero on hand)')
        _write(path, data)
    return {'ok': True, 'removed': part_id, 'ledger_preserved': True}


class SourceReview(BaseModel):
    source_type: Literal['purchase_reference', 'existing_owned_stock', 'other', 'unknown']
    reference: str = Field(default='', max_length=180)
    notes: str = Field(default='', max_length=500)


@router.put('/source-reviews/{event_id}')
def record_source_review(event_id: str, payload: SourceReview, request: Request):
    """Office explanation of a counted stock adjustment, not an accounting posting."""
    actor = _guard(request, write=True)
    if payload.source_type != 'unknown' and len(payload.reference.strip()) < 3:
        raise HTTPException(422, 'Reference or description required to document a source')
    with _locked(request):
        path = _path(request); data = _read(path)
        source = next((e for e in data['events'] if e.get('id') == event_id), None)
        if not source or source.get('movement') != 'count' or source.get('delta') == 0:
            raise HTTPException(404, 'Physical count adjustment not found')
        review = {'event_id': event_id, 'source_type': payload.source_type,
                  'reference': payload.reference.strip(), 'notes': payload.notes.strip(),
                  'actor': actor, 'reviewed_at': datetime.now(timezone.utc).isoformat()}
        data['source_reviews'][event_id] = review
        data['review_history'].append(review)
        _write(path, data)
    return {'ok': True, 'review': review, 'accounting_posted': False}


@router.get('/reconciliation')
def reconciliation(request: Request):
    """Office report of tracked quantities and unresolved physical-count sources.

    These are quantities only, not expense, valuation, tax or procurement entries.
    """
    _guard(request, write=True)
    view = _view(request)
    data = _read(_path(request))
    counted = []
    for e in reversed(data['events']):
        if e.get('movement') != 'count' or e.get('delta') == 0:
            continue
        review = data['source_reviews'].get(e.get('id'))
        counted.append({'event_id': e.get('id'), 'employee_id': e.get('employee_id'),
                        'part_id': e.get('part_id'), 'quantity_change': e.get('delta'),
                        'created_at': e.get('created_at'), 'reason': e.get('reason'),
                        'source_status': 'source_documented' if review and review.get('source_type') != 'unknown' else 'unverified',
                        'review': review or None})
    return {'ok': True, 'items': view['catalog'], 'counts': {'pending_source_review': sum(
        1 for e in counted if e['source_status'] == 'unverified')},
        'physical_count_sources': counted[:300], 'source_rows_truncated': len(counted) > 300,
        'recent_movements': _movement_history(data, _parts(request), _people(request)),
        'financial_values_posted': False, 'warehouse_van_totals_are_quantities_only': True}


class Movement(BaseModel):
    employee_id: str = Field(min_length=1, max_length=120)
    part_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=0, le=100000)
    movement: Literal['load', 'return', 'used', 'count']
    reason: str = Field(min_length=3, max_length=300)
    request_id: str = Field(min_length=8, max_length=120)


def _apply_movement(payload: Movement, request: Request, actor: str):
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
        source_status = ('opening_or_adjusted_count_unverified' if delta != 0 else 'count_confirmed_no_change') if payload.movement == 'count' else ('warehouse_transfer' if payload.movement in ('load','return') else 'job_consumption')
        event = {'id': uuid.uuid4().hex, 'request_id': payload.request_id,
                 'employee_id': payload.employee_id, 'part_id': payload.part_id,
                 'quantity': payload.quantity, 'movement': payload.movement,
                 'source_status': source_status,
                 'delta': delta, 'warehouse_delta': warehouse_delta,
                 'reason': payload.reason.strip(), **_actor_fields(request),
                 'created_at': datetime.now(timezone.utc).isoformat()}
        data['events'].append(event)
        van['items'].setdefault(payload.part_id, {'minimum': None, 'target': None})
        _write(path, data)
    return {'ok': True, 'duplicate': False, 'event_id': event['id'], 'van_quantity': existing + delta}


@router.get('/events')
def recent_events(request: Request, limit: int = 100):
    _guard(request)
    data = _read(_path(request))
    role = getattr(request.state, 'auth_role', '')
    owner = None
    if role in ('tech', 'lead'):
        from app.routers.pds_scheduling import _current_employee_id
        owner = _current_employee_id(request, request.state.auth_user)
    return {'ok': True, 'items': _movement_history(data, _parts(request), _people(request), limit=limit, employee_id=owner)}


@router.get('/history')
def change_history(request: Request, limit: int = 100):
    _guard(request)
    data = _read(_path(request))
    rows = data.get('change_history', [])
    if getattr(request.state, 'auth_role', '') in ('tech', 'lead'):
        from app.routers.pds_scheduling import _current_employee_id
        owner = _current_employee_id(request, request.state.auth_user)
        rows = [row for row in rows if row.get('employee_id') == owner]
    return {'ok': True, 'items': rows[-max(1, min(limit, 300)):][::-1]}



@router.post('/movements')
def movement(payload: Movement, request: Request):
    # Field staff may record only *their own* van's actual usage or count.
    # Warehouse transfers and inter-van transfers remain office-managed.
    if payload.movement in ('load', 'return'):
        actor = _guard(request, write=True)
    else:
        actor = _van_write(request, payload.employee_id)
    return _apply_movement(payload, request, actor)


class CompletionUsage(BaseModel):
    job_id: str = Field(min_length=1, max_length=120)
    form_id: str = Field(min_length=1, max_length=120)
    employee_id: str = Field(min_length=1, max_length=120)
    part_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=1, le=100000)


@router.post('/completion-usage')
def completion_usage(payload: CompletionUsage, request: Request):
    """Record an explicitly selected part after its completion form is saved.

    A single (form, van, part) can only be deducted once. Free text is never
    parsed into inventory movements. Stock already left warehouse when loaded.
    """
    actor = _guard(request)
    job = request.app.state.calendar_store.get_job(payload.job_id)
    if not isinstance(job, dict):
        raise HTTPException(404, 'Job not found')
    forms = job.get('completion_forms') or []
    saved = next((f for f in forms if isinstance(f, dict) and str(f.get('id')) == payload.form_id), None)
    if saved is None:
        raise HTTPException(404, 'Saved completion form not found on this job')
    person = _people(request).get(payload.employee_id)
    if not person:
        raise HTTPException(404, 'Van technician is not active')
    technician = str(saved.get('technician_name') or '').strip().casefold()
    employee = str(person.get('name') or '').strip().casefold()
    if not technician or technician != employee:
        raise HTTPException(409, 'Saved completion form technician does not match the selected van')
    # Only exact, structured usage entered on this form may affect stock.
    # Never interpret arbitrary technician free-text notes as an inventory action.
    recorded = next((line.partition(':')[2].strip() for line in
                     str(saved.get('parts_used') or '').splitlines()
                     if line.startswith('Van stock used:')), '')
    matches = [segment.strip() for segment in recorded.split(';')]
    if not any(segment.startswith(f'{payload.quantity} × ') and
               segment.endswith(f'[{payload.part_id}]') for segment in matches):
        raise HTTPException(409, 'Part and quantity not recorded in saved completion form')
    role = getattr(request.state, 'auth_role', '')
    if role not in ('office', 'office_admin'):
        user = request.state.auth_user
        username = str(user.get('name') or user.get('username') or '').strip().casefold()
        if not username or username != employee:
            raise HTTPException(403, 'Only your own van usage can be recorded')
    # The deterministic request key prevents a second deduction from refresh,
    # retries, or resubmission. A changed quantity instead produces 409.
    source_key = f'{payload.job_id}:{payload.form_id}:{payload.employee_id}:{payload.part_id}'
    request_key = 'completion:' + hashlib.sha256(source_key.encode('utf-8')).hexdigest()
    reason = f'Completion {str(job.get("job_number") or payload.job_id)[:80]} / form {payload.form_id[:80]}'
    item = Movement(employee_id=payload.employee_id, part_id=payload.part_id,
                    quantity=payload.quantity, movement='used', reason=reason,
                    request_id=request_key)
    return _apply_movement(item, request, actor)


class VanTransfer(BaseModel):
    from_employee_id: str = Field(min_length=1, max_length=120)
    to_employee_id: str = Field(min_length=1, max_length=120)
    part_id: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=1, le=100000)
    reason: str = Field(min_length=3, max_length=300)
    request_id: str = Field(min_length=8, max_length=120)


@router.post('/transfers')
def van_to_van(payload: VanTransfer, request: Request):
    """Atomic van-to-van movement; warehouse balance is unchanged."""
    actor = _guard(request, write=True)
    if payload.from_employee_id == payload.to_employee_id:
        raise HTTPException(422, 'Choose a different destination van')
    with _locked(request):
        path = _path(request)
        data = _read(path)
        if payload.part_id not in _parts(request):
            raise HTTPException(404, 'Part not in PDS Parts List')
        source = data['vans'].get(payload.from_employee_id)
        destination = data['vans'].get(payload.to_employee_id)
        if not source or not destination or not source.get('enabled', True) or not destination.get('enabled', True):
            raise HTTPException(404, 'Both van tickets must be active')
        out_id = payload.request_id + ':out'
        prior = next((e for e in data['events'] if e.get('request_id') == out_id), None)
        if prior:
            if (prior.get('employee_id') != payload.from_employee_id or
                prior.get('counterparty') != payload.to_employee_id or
                prior.get('part_id') != payload.part_id or
                prior.get('quantity') != payload.quantity or
                prior.get('reason') != payload.reason.strip()):
                raise HTTPException(409, 'Transfer ID already used for different details')
            return {'ok': True, 'duplicate': True, 'event_id': prior['id']}
        balances, _ = _balances(data)
        if balances.get((payload.from_employee_id, payload.part_id), 0) < payload.quantity:
            raise HTTPException(409, 'Insufficient source van stock')
        now = datetime.now(timezone.utc).isoformat()
        common = {'part_id': payload.part_id, 'quantity': payload.quantity,
                  'warehouse_delta': 0, 'reason': payload.reason.strip(),
                  **_actor_fields(request), 'created_at': now}
        pair_id = uuid.uuid4().hex
        out = dict(common, id=uuid.uuid4().hex, request_id=out_id,
                   employee_id=payload.from_employee_id, counterparty=payload.to_employee_id,
                   movement='transfer_out', delta=-payload.quantity, pair_id=pair_id)
        into = dict(common, id=uuid.uuid4().hex, request_id=payload.request_id + ':in',
                    employee_id=payload.to_employee_id, counterparty=payload.from_employee_id,
                    movement='transfer_in', delta=payload.quantity, pair_id=pair_id)
        data['events'].extend([out, into])
        destination['items'].setdefault(payload.part_id, {'minimum': None, 'target': None})
        _write(path, data)
    return {'ok': True, 'duplicate': False, 'event_id': out['id']}
