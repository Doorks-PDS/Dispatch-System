"""PDS-only purchase orders. Existing estimate/invoice stores are untouched."""
from __future__ import annotations
import json, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix='/pds-purchase-orders', tags=['pds-purchase-orders'])
_lock = RLock()

class POInput(BaseModel):
    data: dict

def _guard(request: Request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Login required')
    if getattr(request.state, 'auth_role', None) not in ('office', 'office_admin'):
        raise HTTPException(403, 'Office access required')
    if request.session.get('active_platform', 'pds') not in ('pds', None):
        raise HTTPException(403, 'Switch to PDS workspace')

def _paths(request: Request):
    folder = Path(request.app.state.data_dir) / 'pds_purchase_orders'
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'records.json', folder / 'sequence.json'

def _read(path: Path, default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8'))

def _write(path: Path, data):
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)

def _clean(data: dict):
    allowed = ('vendor','vendor_contact','work_order','customer','date','needed_by','description',
               'item_type','quantity','unit_cost','tax','shipping','total','status','received_status',
               'payment_status','notes','invoice_reference')
    if not isinstance(data, dict): raise HTTPException(400, 'Invalid PO')
    result = {}
    for key in allowed:
        value = data.get(key, '')
        if not isinstance(value, (str, int, float, type(None))): raise HTTPException(400, 'Invalid field')
        if len(str(value)) > 4000: raise HTTPException(400, 'Field too long')
        result[key] = value
    return result

@router.get('')
def list_orders(request: Request):
    _guard(request)
    with _lock:
        records, _ = _paths(request)
        return {'items': _read(records, [])}

@router.post('')
def create_order(payload: POInput, request: Request):
    _guard(request)
    with _lock:
        records, sequence = _paths(request)
        items = _read(records, [])
        last = int(_read(sequence, {'last':0}).get('last', 0))
        for item in items:
            match = re.fullmatch(r'PO-(\d+)', str(item.get('po_number', '')))
            if match: last = max(last, int(match.group(1)))
        number = f'PO-{last+1:05d}'
        _write(sequence, {'last':last+1})
        now = datetime.now(timezone.utc).isoformat()
        record = {'id':str(uuid.uuid4()), 'po_number':number, 'created_at':now, 'updated_at':now,
                  **_clean(payload.data)}
        items.append(record)
        _write(records, items)
        return record

@router.patch('/{record_id}')
def update_order(record_id: str, payload: POInput, request: Request):
    _guard(request)
    with _lock:
        records, _ = _paths(request)
        items = _read(records, [])
        for item in items:
            if item.get('id') == record_id:
                item.update(_clean(payload.data))
                item['updated_at'] = datetime.now(timezone.utc).isoformat()
                _write(records, items)
                return item
        raise HTTPException(404, 'Purchase order not found')
