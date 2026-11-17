"""PDS optional technician assignments and restricted personal work queue.

Assignments are tentative, may remain empty, and do not alter job status or date.
No distance/travel-time estimates are made from unverified addresses.
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix='/pds-scheduling', tags=['pds-scheduling'])
DOOR_TYPES = ('Automatic Door', 'Man Door', 'Storefront Door', 'Herculite Door',
              'Roll Up', 'Glass', 'Roll/Swing Gate', 'Other')


def _identity(request: Request):
    user = getattr(request.state, 'auth_user', None)
    role = str(getattr(request.state, 'auth_role', '') or '')
    if not isinstance(user, dict) or role not in ('office_admin', 'office', 'lead', 'tech'):
        raise HTTPException(403, 'PDS sign-in required')
    if request.session.get('active_platform') != 'pds':
        raise HTTPException(403, 'Select the PDS workspace')
    return user, role


def _admin(request: Request):
    _, role = _identity(request)
    if role != 'office_admin':
        raise HTTPException(403, 'PDS office administrator required')


def _dispatcher(request: Request):
    _, role = _identity(request)
    if role not in ('office', 'office_admin'):
        raise HTTPException(403, 'PDS office access required for scheduling')


def _people(request: Request):
    """Active staff from PDS employees and sign-in directory; no duplicate names.

    An office-only login without a separate employee row is still assignable.
    Avoid exposing credentials or other private login fields in the roster.
    """
    raw_employees = request.app.state.employees_store.list()
    if not isinstance(raw_employees, list):
        raise HTTPException(503, 'Employee directory unavailable')
    users_store = getattr(request.app.state, 'users_store', None)
    users = users_store.list_users() if users_store else []
    if not isinstance(users, list):
        users = []
    roster = []
    for item in raw_employees:
        if not isinstance(item, dict) or item.get('active') is False:
            continue
        role = str(item.get('role') or '').strip().lower()
        if role not in ('office_admin', 'office', 'lead', 'tech'):
            continue
        row = {'id': str(item.get('id') or ''), 'name': str(item.get('name') or ''),
               'email': str(item.get('email') or ''), 'role': role,
               'login_user_id': str(item.get('login_user_id') or '')}
        if row['id'] and row['name']:
            roster.append(row)
    for user in users:
        if not isinstance(user, dict) or user.get('active') is False:
            continue
        role = str(user.get('role') or '').strip().lower()
        if role not in ('office_admin', 'office', 'lead', 'tech'):
            continue
        uid = str(user.get('id') or '').strip()
        mail = str(user.get('email') or '').strip()
        name = str(user.get('name') or user.get('username') or '').strip()
        if not uid or not name:
            continue
        linked = [e for e in roster if e['login_user_id'] == uid or
                  (mail and e['email'].casefold() == mail.casefold()) or
                  (e['name'].casefold() == name.casefold())]
        if len(linked) == 1:
            linked[0]['login_user_id'] = uid
            linked[0]['role'] = role
        elif not linked:
            roster.append({'id': uid, 'login_user_id': uid, 'name': name,
                           'email': mail, 'role': role})
    return roster


def _person(request: Request, person_id: str):
    matches = [e for e in _people(request) if e['id'] == person_id]
    if len(matches) != 1:
        raise HTTPException(404, 'Active staff profile not found')
    return matches[0]


def _technician(request: Request, technician_id: str):
    person = _person(request, technician_id)
    if person['role'] not in ('tech', 'lead'):
        raise HTTPException(403, 'Skill ratings are only available for techs and leads')
    # Skill persistence requires the existing employee record, not a login-only row.
    record = next((e for e in request.app.state.employees_store.list()
                   if str(e.get('id') or '') == technician_id), None)
    if not isinstance(record, dict):
        raise HTTPException(409, 'Create the technician employee profile before rating skills')
    return record


def _current_employee_id(request: Request, user: dict):
    employees = _people(request)
    uid = str(user.get('id') or '').strip().casefold()
    mail = str(user.get('email') or '').strip().casefold()
    name = str(user.get('name') or user.get('username') or '').strip().casefold()
    for field, value in (('login_user_id', uid), ('email', mail), ('name', name)):
        if not value:
            continue
        matches = [e for e in employees if str(e.get(field) or '').strip().casefold() == value]
        if len(matches) == 1:
            return str(matches[0]['id'])
        if len(matches) > 1:
            raise HTTPException(409, 'Staff identity ambiguous; contact the office')
    raise HTTPException(403, 'Your employee profile is not linked to your login')


@router.get('/assignable-staff')
def assignable_staff(request: Request):
    _dispatcher(request)
    return {'ok': True, 'staff': [{'id': e['id'], 'name': e['name'], 'role': e['role']}
                                  for e in _people(request)],
            'note': 'Every active PDS staff member may be assigned to dispatches or sales leads'}


class Assignment(BaseModel):
    lead_id: str = Field(default='', max_length=80)
    employee_ids: list[str] = Field(default_factory=list, max_length=30)
    technician_ids: list[str] = Field(default_factory=list, max_length=30)  # older clients
    tentative: bool = True


@router.put('/jobs/{job_id}/assignment')
def assign(job_id: str, payload: Assignment, request: Request):
    """Office-admin assignment; shared calendar visibility and job status unchanged."""
    _dispatcher(request)
    store = request.app.state.calendar_store
    job = store.get_job(job_id)
    if not isinstance(job, dict):
        raise HTTPException(404, 'Job not found')
    ids = payload.employee_ids if payload.employee_ids else payload.technician_ids
    if len(set(ids)) != len(ids):
        raise HTTPException(422, 'Duplicate employee IDs')
    for person_id in ids:
        if not person_id or len(person_id) > 80:
            raise HTTPException(422, 'Invalid employee ID')
        _person(request, person_id)
    if payload.lead_id:
        _person(request, payload.lead_id)  # office staff can coordinate sales leads too
        if payload.lead_id in ids:
            raise HTTPException(422, 'Assigned lead should not be listed twice')
    update = {'assigned_lead_id': payload.lead_id,
              'assigned_employee_ids': ids,
              'assignment_tentative': bool(payload.tentative)}
    saved = store.update_job(job_id, update)
    if (saved.get('assigned_lead_id', '') != payload.lead_id or
            saved.get('assigned_employee_ids', []) != ids):
        raise HTTPException(503, 'Assignment storage not enabled')
    return {'ok': True, 'job_id': job_id, 'assignment': update,
            'job_date_unchanged': str(saved.get('date') or '') == str(job.get('date') or ''),
            'status_unchanged': str(saved.get('status') or '') == str(job.get('status') or ''),
            'shared_calendar_unchanged': True}


class Skills(BaseModel):
    ratings: dict[str, int] = Field(default_factory=dict)
    preferences: list[str] = Field(default_factory=list, max_length=20)
    can_lead_crew: bool = False


@router.put('/technicians/{technician_id}/skills')
def save_skills(technician_id: str, payload: Skills, request: Request):
    _admin(request)
    _technician(request, technician_id)
    if any(k not in DOOR_TYPES or isinstance(v, bool) or v < 1 or v > 10
           for k, v in payload.ratings.items()):
        raise HTTPException(422, 'Use recognized door types and integer skill ratings 1–10')
    if any(not isinstance(v, str) or len(v) > 100 for v in payload.preferences):
        raise HTTPException(422, 'Invalid scheduling preference')
    profile = {'ratings': payload.ratings, 'preferences': payload.preferences,
               'can_lead_crew': payload.can_lead_crew}
    saved = request.app.state.employees_store.update(technician_id, {'scheduling_profile': profile})
    if not isinstance(saved, dict) or saved.get('scheduling_profile') != profile:
        raise HTTPException(503, 'Skill profile storage not enabled')
    return {'ok': True, 'technician_id': technician_id, 'profile': profile}


@router.get('/technicians/{technician_id}/skills')
def read_skills(technician_id: str, request: Request):
    _admin(request)
    row = _technician(request, technician_id)
    return {'technician_id': technician_id, 'profile': row.get('scheduling_profile') or
            {'ratings': {}, 'preferences': [], 'can_lead_crew': False},
            'unrated_means_unknown': True}


@router.get('/my-jobs')
def my_jobs(request: Request, day: str = ''):
    """Only assigned tickets for the signed-in staff member, including sales leads."""
    user, role = _identity(request)
    if role not in ('office_admin', 'office', 'tech', 'lead'):
        raise HTTPException(403, 'Staff access required')
    employee_id = _current_employee_id(request, user)
    if day:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise HTTPException(422, 'Date must be YYYY-MM-DD')
    jobs = request.app.state.calendar_store.list_jobs()
    found = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        assigned = list(dict.fromkeys((job.get('assigned_employee_ids') or []) + (job.get('assigned_technician_ids') or [])))
        if employee_id not in assigned and str(job.get('assigned_lead_id') or '') != employee_id:
            continue
        if day and str(job.get('date') or '') != day:
            continue
        if str(job.get('status') or '').lower() in ('cancelled', 'canceled'):
            continue
        # Allowlist keeps private office notes and other customers' records out.
        found.append({k: str(job.get(k) or '')[:200] for k in
                      ('id', 'job_number', 'date', 'customer', 'address', 'status', 'contact')})
        found[-1]['tentative'] = bool(job.get('assignment_tentative', True))
    found.sort(key=lambda j: (j['date'], j['job_number']))
    return {'ok': True, 'jobs': found, 'count': len(found),
            'order_type': 'date_and_job_number_not_geographic_distance',
            'note': 'Assignments are tentative and may change; all jobs remain on the shared calendar'}
