from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/saddleback", tags=["saddleback"])


def _store(request: Request):
    return request.app.state.saddleback_store


def _require(request: Request, x_api_key: Optional[str]):
    return request.app.state.require_key(x_api_key, request)


def _auth_role(request: Request) -> str:
    return str(getattr(request.state, "auth_role", "") or "")


def _can_write(request: Request) -> bool:
    return _auth_role(request) in {"admin", "office_admin"}


class SaddlebackPayload(BaseModel):
    orders: Optional[List[Dict[str, Any]]] = None
    expenses: Optional[List[Dict[str, Any]]] = None
    purchases: Optional[List[Dict[str, Any]]] = None


@router.get("")
def get_saddleback(request: Request, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    return {"ok": True, "data": _store(request).get_all()}


@router.put("")
def save_saddleback(request: Request, payload: SaddlebackPayload, x_api_key: Optional[str] = Header(default=None)):
    _require(request, x_api_key)
    if not _can_write(request):
        raise HTTPException(status_code=403, detail="Only office admin users can save Saddleback data")
    return {"ok": True, "data": _store(request).replace_all(payload.dict(exclude_unset=True))}


@router.get('/migration-preview')
def preview_saddleback_migration(request: Request, x_api_key: Optional[str] = Header(default=None)):
    """Read-only comparison of historical SDC records with the current SDC workspace."""
    _require(request, x_api_key)
    from app.routers import workspaces as ws

    ws.guard(request, 'sdc', 'orders')
    legacy = _store(request).get_all()
    mapping = {'orders': 'orders', 'expenses': 'expenses', 'purchases': 'expenses'}
    result = {}
    for kind, destination in mapping.items():
        existing = ws.load(ws.location(request, 'sdc', destination))
        present = {str(x.get('legacy_saddleback_key', '')) for x in existing}
        source = [r for r in legacy.get(kind, []) if isinstance(r, dict)]
        pending = sum(1 for r in source if _sdc_legacy_key(kind, r) not in present)
        result[kind] = {'source': len(source), 'already_imported': len(source) - pending, 'to_import': pending, 'destination': destination}
    return {'ok': True, 'preview': result, 'note': 'Preview only. No records have been changed.'}


def _sdc_legacy_key(kind: str, row: Dict[str, Any]) -> str:
    """Stable legacy identity even when an old record lacks an ID."""
    import hashlib, json
    identity = str(row.get('id') or '').strip()
    if not identity:
        identity = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    return kind + ':' + identity


@router.post('/migrate-to-sdc')
def migrate_saddleback_to_sdc(request: Request, x_api_key: Optional[str] = Header(default=None)):
    """Explicit, additive, repeat-safe migration; never alters the legacy source."""
    _require(request, x_api_key)
    from app.routers import workspaces as ws
    from datetime import datetime, timezone
    from pathlib import Path
    import shutil, uuid

    ws.guard(request, 'sdc', 'orders')
    ws.guard(request, 'sdc', 'expenses')
    legacy = _store(request).get_all()
    with ws._lock:
        paths = {kind: ws.location(request, 'sdc', kind) for kind in ('orders', 'expenses')}
        existing = {kind: ws.load(path) for kind, path in paths.items()}
        seen = {kind: {str(r.get('legacy_saddleback_key', '')) for r in rows} for kind, rows in existing.items()}
        additions = {'orders': [], 'expenses': []}
        counts = {'orders': 0, 'expenses': 0, 'purchases': 0}
        for source_kind, destination in (('orders', 'orders'), ('expenses', 'expenses'), ('purchases', 'expenses')):
            for original in legacy.get(source_kind, []):
                if not isinstance(original, dict):
                    continue
                key = _sdc_legacy_key(source_kind, original)
                if key in seen[destination]:
                    continue
                row = dict(original)
                # Preserve all original scalar fields and add only migration metadata.
                row['id'] = uuid.uuid4().hex
                row['legacy_saddleback_key'] = key
                row['legacy_saddleback_id'] = str(original.get('id', ''))
                row['source'] = 'historical_saddleback'
                row['legacy_record_type'] = source_kind
                row['migrated_at'] = datetime.now(timezone.utc).isoformat()
                if source_kind == 'orders':
                    row.setdefault('order_number', str(original.get('ref', '')))
                    row.setdefault('customer_name', str(original.get('customer', '')))
                    row.setdefault('total', original.get('total', 0))
                elif source_kind == 'purchases':
                    row.setdefault('description', str(original.get('item', '')))
                    row.setdefault('reference', str(original.get('reference', '')))
                    row.setdefault('expense_type', 'Purchase / Materials')
                else:
                    row.setdefault('description', str(original.get('category', '')))
                additions[destination].append(row)
                seen[destination].add(key)
                counts[source_kind] += 1
        if not any(counts.values()):
            return {'ok': True, 'imported': counts, 'message': 'No new records to import. Existing records were left unchanged.'}
        # Back up every destination that is about to change, before writing either.
        backup_dir = Path(request.app.state.data_dir) / 'sdc_migration_backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup_dir.mkdir(parents=True, exist_ok=False)
        for kind, path in paths.items():
            if additions[kind]:
                if path.exists():
                    shutil.copy2(path, backup_dir / (kind + '.json'))
                else:
                    (backup_dir / (kind + '.was_absent')).touch()
        for kind, rows in additions.items():
            if rows:
                ws.save(paths[kind], existing[kind] + rows)
        return {'ok': True, 'imported': counts, 'message': 'Historical records copied. Original Saddleback records were not changed.'}
