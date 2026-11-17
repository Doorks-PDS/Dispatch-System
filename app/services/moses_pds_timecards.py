"""Bounded, read-only PDS timecard approval counts for office administrators.

No salary, hours, notes or individual timecard content enters the model.
Do not use TimeCardsStore.list(), which currently rewrites the file on reads.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import HTTPException


def pending_approvals(request, month: str = '') -> dict:
    if (not getattr(request.state, 'auth_user', None)
            or getattr(request.state, 'auth_role', None) != 'office_admin'
            or request.session.get('active_platform') != 'pds'):
        raise HTTPException(403, 'PDS office administrator access required')
    if not month:
        month = datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m')
    if not isinstance(month, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise HTTPException(422, 'Month must be YYYY-MM')
    store = getattr(request.app.state, 'timecards_store', None)
    path = getattr(store, 'path', None)
    if path is None:
        raise HTTPException(503, 'PDS timecard store is unavailable')
    file = Path(path)
    if not file.is_file():
        raise HTTPException(503, 'PDS timecards could not be verified')
    try:
        raw = json.loads(file.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(503, 'PDS timecards could not be read') from exc
    if not isinstance(raw, dict) or not isinstance(raw.get('items'), list):
        raise HTTPException(503, 'PDS timecards have an invalid format')
    items = raw['items']
    if any(not isinstance(item, dict) for item in items):
        raise HTTPException(503, 'PDS timecards have an invalid entry')
    selected = [item for item in items if str(item.get('date') or '').startswith(month + '-')]
    # Historical records may encode booleans differently. Unknown values are
    # excluded from the "approved" bucket and reported for manual review.
    approved = 0
    pending = 0
    unrecognized = 0
    for item in selected:
        value = item.get('supervisor_approved', False)
        if value is True or (isinstance(value, str) and value.strip().casefold() in ('yes', 'true', '1')):
            approved += 1
        elif value is False or value is None or (isinstance(value, str) and value.strip().casefold() in ('no', 'false', '0', '')):
            pending += 1
        else:
            unrecognized += 1
    return {'workspace': 'pds', 'month': month, 'total_timecards': len(selected),
            'pending_approval': pending, 'approved': approved,
            'approval_status_needs_review': unrecognized, 'read_only': True,
            'records_changed': False}
