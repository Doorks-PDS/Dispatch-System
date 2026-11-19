"""Admin-only PDS PRIO planning trials, never monetary or payroll operations.

This ledger is exclusively for hypothetical contributions. No investments,
vested benefits, payroll deductions, payments, or financial transfers occur.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/pds-prio-trials', tags=['pds-prio-trials'])
_lock = RLock()


class TrialEntry(BaseModel):
    date: date
    amount: float = Field(gt=0, le=10000000)
    frequency: Literal['Quarterly', 'Monthly', 'One time'] = 'Quarterly'
    notes: str = Field(default='', max_length=240)


def _guard(request: Request):
    if getattr(request.state, 'auth_role', None) != 'office_admin' or not isinstance(getattr(request.state, 'auth_user', None), dict):
        raise HTTPException(403, 'PDS office administrator required')
    if request.session.get('active_platform') != 'pds':
        raise HTTPException(403, 'Switch to PDS workspace')


def _path(request: Request) -> Path:
    root = getattr(request.app.state, 'data_dir', None)
    if not root:
        raise HTTPException(503, 'Durable data path is not configured')
    return Path(root) / 'pds_prio_simulated_trials.json'


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict) or value.get('type') != 'simulation' or not isinstance(value.get('entries'), list):
            raise ValueError('Unexpected PRIO simulation ledger')
        if len(value['entries']) > 10000:
            raise ValueError('Trial ledger requires archiving')
        return value['entries']
    except (ValueError, OSError, UnicodeError) as exc:
        raise HTTPException(503, 'PRIO trial ledger requires review, changes blocked') from exc


def _save(path: Path, entries: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as file:
            json.dump({'type': 'simulation', 'entries': entries}, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@router.get('')
def list_trials(request: Request):
    _guard(request)
    with _lock:
        return {'ok': True, 'simulation_only': True, 'entries': _load(_path(request))}


@router.post('')
def add_trial(body: TrialEntry, request: Request):
    _guard(request)
    cents = round(body.amount * 100)
    if cents < 1:
        raise HTTPException(422, 'Invalid trial amount')
    with _lock:
        path = _path(request)
        entries = _load(path)
        if len(entries) >= 10000:
            raise HTTPException(409, 'Trial limit reached; export for review')
        entry = {'id': str(uuid.uuid4()), 'date': body.date.isoformat(), 'amount_cents': cents,
                 'frequency': body.frequency, 'notes': body.notes.strip(),
                 'created_by': str(request.state.auth_user.get('id') or request.state.auth_user.get('name') or 'admin'),
                 'created_at': datetime.now(timezone.utc).isoformat(), 'simulation_only': True}
        entries.append(entry)
        _save(path, entries)
    return {'ok': True, 'simulation_only': True, 'entry': entry}
