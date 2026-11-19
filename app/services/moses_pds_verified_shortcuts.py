"""Verified PDS chat shortcuts for records the model fallback otherwise cannot see.

Does not execute general writes. The only permitted write is an explicit, unsent
appointment email proposal, still subject to the existing office approval.
"""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException

_JOB_NUMBER = re.compile(r'\b(?:\d{4}-\d{1,4}|\d{6,10})\b')


def respond(request, text: str):
    role = getattr(request.state, 'auth_role', '')
    if request.session.get('active_platform') != 'pds' or role not in ('office_admin', 'office', 'lead'):
        return None
    q = str(text or '').lower()
    if re.search(r'\b(vans?|van stock|inventory)\b', q) and re.search(
        r'\b(restock|low|short|shortage|who has|which (?:van|tech)|where|movement|used|count|unverified|reconcil)', q):
        if 'unverified' in q or 'reconcil' in q:
            if role not in ('office', 'office_admin'):
                return 'Inventory source reconciliation requires PDS office access. No records were changed.'
            from app.routers.pds_van_stock import reconciliation
            data = reconciliation(request)
            pending = [r for r in data['physical_count_sources'] if r['source_status'] == 'unverified']
            lines = [f"PDS stock source review: {data['counts']['pending_source_review']} unresolved physical-count adjustment(s)."]
            for row in pending[:8]:
                lines.append(f"• Part {row['part_id']} · van {row['employee_id']} · change {row['quantity_change']:+} · {row['reason']}")
            lines.append('These are quantity records only; no expenses, purchases or tax entries were posted.')
            return '\n'.join(lines)
        from app.routers.pds_van_stock import overview
        data = overview(request)
        vans = [v for v in data['vans'] if v['enabled']]
        query = re.search(r'\b(?:part|sku|item)\s+([A-Za-z0-9][A-Za-z0-9._/-]{1,40})', text, re.I)
        if query:
            term = query.group(1).casefold()
            matched=[]
            for van in vans:
                for part in van['items']:
                    if term in str(part.get('part_number') or '').casefold():
                        matched.append(f"• {van['employee_name']}: {part['part_number']} · {part['quantity']} on van")
            return '\n'.join([f'Part {query.group(1)} across saved active vans:', *(matched[:15] or ['No matching assigned part found.'])]) + '\nNo inventory was changed.'
        low_vans = [(van, [x for x in van['items'] if x['low']]) for van in vans]
        low_vans = [(v, items) for v, items in low_vans if items]
        warehouse = [p for p in data['catalog'] if p['low']]
        lines = [f"PDS Van Stock: {len(vans)} active van(s), {data['alerts']['vans']} van shortage(s), {len(warehouse)} warehouse alert(s)."]
        for van, items in low_vans[:12]:
            lines.append(f"• {van['employee_name']}: " + '; '.join(
                f"{p['part_number']} needs {p['needed']} (on van {p['quantity']}, min {p['minimum']})" for p in items[:7]))
        if warehouse:
            lines.append('Warehouse: ' + '; '.join(f"{p['part_number']} needs {p['needed']}" for p in warehouse[:8]))
        if not low_vans and not warehouse:
            lines.append('No shortages under the saved thresholds. Items without a minimum cannot be classified as adequately stocked.')
        lines.append('Read from PDS stock records; nothing was ordered or changed.')
        return '\n'.join(lines)

    is_scopes = bool(re.search(r'\b(estimates?|quotes?|scopes?|completion forms?|recommendations?)\b', q) and
                     re.search(r'\b(review|separate|multiple|split|identify|how many)\b', q))
    is_email = bool(re.search(r'\b(appointment|schedule)\b', q) and
                    re.search(r'\b(email|confirmation)\b', q) and
                    re.search(r'\b(prepare|draft|create)\b', q))
    if not is_scopes and not is_email:
        return None
    match = _JOB_NUMBER.search(text)
    if not match:
        return 'Please specify the exact PDS job number so I can verify the saved ticket. Nothing was changed.'
    number = match.group(0)
    store = request.app.state.calendar_store
    job = store.get_by_job_number(number) if hasattr(store, 'get_by_job_number') else None
    if not job:
        jobs = store.all() if hasattr(store, 'all') else store.list_jobs() if hasattr(store, 'list_jobs') else []
        candidates = [j for j in jobs if isinstance(j, dict) and str(j.get('job_number')) == number]
        if len(candidates) == 1:
            job = candidates[0]
    if not job or not job.get('id'):
        return f'No uniquely verified PDS job {number} was found. No changes were made.'
    if is_scopes:
        from app.services.moses_pds_estimate_scopes import inspect
        result = inspect(request, str(job['id']))
        lines = [f"Job {number} · {job.get('customer') or 'Customer not saved'}: "
                 f"{result['proposed_scope_count']} proposed scope(s) from {result['form_count']} completion/recommendation forms."]
        for scope in result['proposed_scopes'][:15]:
            content = scope['scope']
            detail = '; '.join(v[:150] for v in content.values() if v)
            lines.append(f"• Form #{scope['source_form_number']} · {scope['door_location'] or 'location unspecified'} "
                         f"· {scope['status']}: {detail or 'No recommendations recorded'}")
        if result['manual_split_required']:
            lines.append('One or more forms request multiple quotes; the office must confirm how to split them.')
        lines.append('No official estimates were created, numbered or sent.')
        return '\n'.join(lines)
    if re.search(r'\b(?:do not|don.t|never)\s+(?:prepare|draft|create)\b', q):
        return 'No customer notification was prepared or sent.'
    if role != 'office_admin':
        return 'Only a PDS office administrator can prepare a customer notification approval. No email was sent.'
    scheduled = str(job.get('scheduled_date') or '')[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', scheduled):
        return f'Job {number} has no verified scheduled date. Update the Scheduler before preparing a confirmation. No email was prepared.'
    if scheduled < datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat():
        return f'Job {number} is scheduled in the past ({scheduled}). Review the Scheduler before preparing a new confirmation. No email was prepared.'
    from app.services.moses_delivery import _email
    email = next((candidate for k in ('email', 'contact_email', 'customer_email')
                  if (candidate := _email(job.get(k)))), '')
    if not email:
        return f'Job {number} has no saved customer email. Update the contact before preparing a notification. No email was prepared.'
    from app.services.pds_schedule_notifications import propose
    time = str(job.get('scheduled_time') or '').strip()[:30]
    place = str(job.get('address') or '').strip()[:140]
    body = f"Priority Door Systems: Appointment confirmation for job {number} on {scheduled}"
    if time:
        body += f' at {time}'
    if place:
        body += f' at {place}'
    body += '. Please contact our office if the schedule needs to change.'
    result = propose(request, str(job['id']), email, 'appointment',
                     f'PDS Appointment Confirmation — {number}', body)
    return (f"Saved UNSENT appointment email for job {number} to the verified contact {email}. "
            f"Approval ID: {result['proposal']['id']}. Review and approve it in the PDS Scheduler; "
            'no customer message was sent.')
