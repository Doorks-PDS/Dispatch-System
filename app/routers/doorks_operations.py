"""Doorks-only payroll calculation, employee access and financial reconciliation.

No external payroll submission, bank settlement or journal posting is performed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.routers import workspaces as ws, doorks_accounting as ac

router = APIRouter(prefix='/doorks-operations', tags=['doorks-operations'])
_lock = RLock()

class Timecard(BaseModel):
    employee_id: str
    work_date: str
    time_in: str = ''
    time_out: str = ''
    lunch_minutes: int = 0
    pto_hours: float = 0
    holiday_hours: float = 0
    notes: str = ''

class Approval(BaseModel):
    approved: bool

class AccessChange(BaseModel):
    user_id: str
    active: bool

def guard(request: Request):
    ws.guard(request, 'doorks', 'employees')

def money(value):
    try:
        x = Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if not x.is_finite() or x < 0 or x > 999999999:
            raise ValueError()
        return x
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(400, 'Invalid nonnegative financial amount')

def hours(value):
    try:
        x = Decimal(str(value or 0))
        if not x.is_finite() or x < 0 or x > 24:
            raise ValueError()
        return x
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(400, 'Hours must be between 0 and 24')

def clock(value):
    for fmt in ('%I:%M %p', '%I:%M%p', '%H:%M'):
        try:
            return datetime.strptime(value.strip().upper(), fmt)
        except (ValueError, AttributeError):
            continue
    raise HTTPException(400, 'Enter a time such as 8:30 AM or 5:00 PM')

def calculate(data: Timecard):
    try:
        date.fromisoformat(data.work_date)
    except ValueError:
        raise HTTPException(400, 'Invalid work date')
    if data.lunch_minutes < 0 or data.lunch_minutes > 240:
        raise HTTPException(400, 'Lunch must be 0–240 minutes')
    pto, holiday = hours(data.pto_hours), hours(data.holiday_hours)
    worked = Decimal(0)
    if bool(data.time_in) != bool(data.time_out):
        raise HTTPException(400, 'Both time in and time out are required')
    if data.time_in:
        start, end = clock(data.time_in), clock(data.time_out)
        elapsed = Decimal(str((end-start).total_seconds()/3600))
        if elapsed <= 0:
            elapsed += 24
        if elapsed > 16:
            raise HTTPException(400, 'Shift longer than 16 hours requires manual review')
        worked = elapsed - Decimal(data.lunch_minutes)/60
        if worked < 0:
            raise HTTPException(400, 'Lunch exceeds shift length')
    if not data.time_in and pto == 0 and holiday == 0:
        raise HTTPException(400, 'Enter shift times or PTO/holiday hours')
    if worked + pto + holiday > Decimal(24):
        raise HTTPException(400, 'Total work, PTO and holiday hours cannot exceed 24 per day')
    regular = min(worked, Decimal(8))
    overtime = max(Decimal(0), worked-Decimal(8))
    rounded = lambda x: float(x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return dict(regular_hours=rounded(regular), overtime_hours=rounded(overtime),
                actual_hours=rounded(worked), pto_hours=rounded(pto), holiday_hours=rounded(holiday))

def staff(request):
    return ws.load(ws.location(request,'doorks','employees'))

def cards(request):
    return ws.load(ws.location(request,'doorks','payroll'))

@router.post('/timecards')
def create_timecard(data: Timecard, request: Request):
    guard(request)
    with _lock:
        employee = next((e for e in staff(request) if e.get('id') == data.employee_id), None)
        if not employee:
            raise HTTPException(404, 'Employee not found')
        if str(employee.get('status','Active')).lower() != 'active':
            raise HTTPException(409, 'Cannot add a new timecard for an inactive employee')
        result = calculate(data)
        rows = cards(request)
        if any(r.get('employee_id') == data.employee_id and r.get('work_date') == data.work_date for r in rows):
            raise HTTPException(409, 'Timecard already exists for this employee and date')
        import uuid
        record = dict(id=uuid.uuid4().hex, employee_id=data.employee_id, employee=employee.get('name',''),
                      work_date=data.work_date, time_in=data.time_in, time_out=data.time_out,
                      lunch_minutes=data.lunch_minutes, notes=data.notes[:4000], **result,
                      supervisor_approved='No', created_at=datetime.now(timezone.utc).isoformat(),
                      calculation_version=1)
        rows.append(record)
        ws.save(ws.location(request,'doorks','payroll'),rows)
        return {'item':record}

@router.put('/timecards/{item_id}')
def update_timecard(item_id: str, data: Timecard, request: Request):
    guard(request)
    with _lock:
        rows = cards(request)
        row = next((r for r in rows if r.get('id') == item_id), None)
        if row is None:
            raise HTTPException(404, 'Timecard not found')
        employee = next((e for e in staff(request) if e.get('id') == data.employee_id), None)
        if employee is None:
            raise HTTPException(404, 'Employee not found')
        if any(r.get('id') != item_id and r.get('employee_id') == data.employee_id and r.get('work_date') == data.work_date for r in rows):
            raise HTTPException(409, 'Timecard already exists for this employee and date')
        result = calculate(data)
        now = datetime.now(timezone.utc).isoformat()
        row.update(employee_id=data.employee_id, employee=employee.get('name', ''), work_date=data.work_date,
                   time_in=data.time_in, time_out=data.time_out, lunch_minutes=data.lunch_minutes,
                   notes=data.notes[:4000], **result, supervisor_approved='No', approved_by='',
                   approved_at='', updated_at=now, calculation_version=1)
        ws.save(ws.location(request, 'doorks', 'payroll'), rows)
        return {'item': row, 'approval_reset': True}

@router.post('/timecards/{item_id}/approval')
def approve_timecard(item_id: str, data: Approval, request: Request):
    guard(request)
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Office Admin required for supervisor approval')
    with _lock:
        rows=cards(request)
        row=next((r for r in rows if r.get('id')==item_id),None)
        if row is None: raise HTTPException(404,'Timecard not found')
        if not row.get('calculation_version'):
            raise HTTPException(409,'Legacy timecard must be recalculated before approval')
        row['supervisor_approved']='Yes' if data.approved else 'No'
        row['approved_by']=request.state.auth_user.get('id') if data.approved else ''
        row['approved_at']=datetime.now(timezone.utc).isoformat() if data.approved else ''
        ws.save(ws.location(request,'doorks','payroll'),rows)
        return {'item':row}

@router.get('/pay-period')
def pay_period(start: str, end: str, request: Request):
    guard(request)
    try:
        first,last=date.fromisoformat(start),date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400,'Dates must be YYYY-MM-DD')
    if last < first or (last-first).days>45:
        raise HTTPException(400,'Pay period must be 1–46 days')
    employees={e.get('id'):e for e in staff(request)}
    groups=defaultdict(list)
    for r in cards(request):
        if start<=str(r.get('work_date',''))<=end:
            groups[r.get('employee_id') or r.get('employee')].append(r)
    output=[]
    for employee_id,records in groups.items():
        emp=employees.get(employee_id,{})
        rate=money(emp.get('hourly_rate',0))
        totals={k:sum(Decimal(str(r.get(k,0) or 0)) for r in records) for k in ('regular_hours','overtime_hours','pto_hours','holiday_hours')}
        pending=sum(r.get('supervisor_approved')!='Yes' or not r.get('calculation_version') for r in records)
        # Advisory only: PTO bank is not debited automatically. Do not silently modify employee records.
        pto_bank = hours(emp.get('pto_bank', 0)) if emp else Decimal(0)
        pto_exceeds_bank = totals['pto_hours'] > pto_bank
        gross=(totals['regular_hours']+totals['pto_hours']+totals['holiday_hours'])*rate+totals['overtime_hours']*rate*Decimal('1.5')
        output.append(dict(employee_id=employee_id,employee=emp.get('name') or records[0].get('employee',''),
                           hourly_rate=float(rate), **{k:float(v) for k,v in totals.items()},
                           pending_approval=pending, timecards=len(records),
                           estimated_gross=float(gross.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),
                           pto_bank_hours=float(pto_bank), pto_exceeds_bank=pto_exceeds_bank,
                           ready_for_export=pending==0 and bool(emp) and not pto_exceeds_bank))
    return {'start':start,'end':end,'employees':output,
            'estimated_gross_total':round(sum(e['estimated_gross'] for e in output),2),
            'note':'Gross wages estimate only. PTO balances are advisory and not automatically debited. Taxes, deductions, jurisdiction-specific wage rules and payroll transmission are not included.'}

@router.post('/employees/{employee_id}/access')
def change_access(employee_id: str, data: AccessChange, request: Request):
    guard(request)
    with _lock:
        employees=staff(request)
        employee=next((e for e in employees if e.get('id')==employee_id),None)
        if employee is None: raise HTTPException(404,'Employee not found')
        user=request.app.state.users_store.get_by_id(data.user_id)
        if user is None: raise HTTPException(404,'Login account not found')
        if data.user_id==request.state.auth_user.get('id') and not data.active:
            raise HTTPException(409,'Cannot deactivate your own account')
        if employee.get('auth_user_id') and employee['auth_user_id']!=data.user_id:
            raise HTTPException(409,'Employee is linked to a different account')
        if any(e.get('auth_user_id')==data.user_id and e.get('id')!=employee_id for e in employees):
            raise HTTPException(409,'Login account is already linked to another employee')
        if data.active and str(employee.get('status','Active')).lower()!='active':
            raise HTTPException(409,'Activate the employee record before enabling login')
        try:
            changed=request.app.state.users_store.set_active(data.user_id,data.active)
        except ValueError as exc:
            raise HTTPException(409,str(exc))
        employee['auth_user_id']=data.user_id
        employee['access_active']=bool(changed.get('active'))
        employee['access_updated_at']=datetime.now(timezone.utc).isoformat()
        ws.save(ws.location(request,'doorks','employees'),employees)
        return {'employee_id':employee_id,'user_id':data.user_id,'active':employee['access_active']}

@router.get('/reconciliation')
def reconciliation(request: Request):
    guard(request)
    from app.routers.doorks_workflow import amt
    docs=ws.load(ws.location(request,'doorks','estimates_invoices'))
    orders=ws.load(ws.location(request,'doorks','purchase_orders'))
    ar=ac.read(ac.base(request)/'receivables.json')
    bills=ac.read(ac.base(request)/'supplier_bills.json')
    generic=ac.read(ac.base(request)/'inventory.json')
    issues=[]
    by_invoice={r.get('source_invoice_id'):r for r in ar if r.get('source_invoice_id')}
    for invoice in (d for d in docs if str(d.get('document_type','')).lower()=='invoice'):
        rec=by_invoice.get(invoice.get('id'))
        if rec is None:
            issues.append(dict(type='invoice_not_linked',reference=invoice.get('document_number',''),message='Invoice has not been linked to Accounts Receivable'))
        elif money(rec.get('amount')) != money(invoice.get('total') or invoice.get('amount')):
            issues.append(dict(type='invoice_amount_mismatch',reference=invoice.get('document_number',''),message='Invoice and receivable totals differ'))
    seen_invoices=set()
    for r in ar:
        number=str(r.get('invoice_number') or '').strip()
        if number and number in seen_invoices:
            issues.append(dict(type='duplicate_receivable',reference=number,message='Multiple receivable records share the same invoice number'))
        seen_invoices.add(number)
    seen_bills=set()
    for b in bills:
        key=(str(b.get('source_po_id') or ''),str(b.get('bill_number') or '').strip())
        if key in seen_bills:
            issues.append(dict(type='duplicate_supplier_bill',reference=key[1],message='Supplier bill appears more than once for this purchase order'))
        seen_bills.add(key)
    order_ids={p.get('id') for p in orders}
    for bill in bills:
        if bill.get('source_po_id') and bill['source_po_id'] not in order_ids:
            issues.append(dict(type='missing_purchase_order',reference=bill.get('bill_number',''),message='Supplier bill references a missing purchase order'))
    # Manual ledger and linked workflow bills are separate stores. Flag potential duplicates
    # without deleting, moving, or auto-posting any financial record.
    from app.routers import accounting_ledger as ledger
    manual_bills=ledger.load(ledger.path(request,'doorks','bills'))
    linked_keys={(str(b.get('vendor') or '').strip().casefold(),str(b.get('bill_number') or '').strip().casefold()) for b in bills}
    for manual in manual_bills:
        key=(str(manual.get('supplier') or '').strip().casefold(),str(manual.get('bill_number') or '').strip().casefold())
        if all(key) and key in linked_keys:
            issues.append(dict(type='possible_cross_ledger_duplicate',reference=manual.get('bill_number',''),message='Bill also exists in the linked PO workflow; review before recording payments'))
    for row in ar+bills:
        if money(row.get('paid'))>money(row.get('amount')):
            issues.append(dict(type='overpayment',reference=row.get('invoice_number') or row.get('bill_number',''),message='Payments exceed recorded total'))
    return dict(invoices=len([d for d in docs if str(d.get('document_type','')).lower()=='invoice']),
                purchase_orders=len(orders),receivables=len(ar),supplier_bills=len(bills),
                outstanding_customer_invoices=float(sum((max(Decimal(0),money(r.get('amount'))-money(r.get('paid'))) for r in ar),Decimal(0))),
                outstanding_supplier_bills=float(sum((max(Decimal(0),money(r.get('amount'))-money(r.get('paid'))) for r in bills),Decimal(0))),
                inventory_intake_records=len(generic),issues=issues,
                note='Reconciliation of internal Doorks records only; not bank reconciliation or general ledger posting.')


# Revision 24: derived stock balances. Catalog entries remain visible when on-hand is zero.
# The receiving journal is the source of goods received; manual changes are append-only.
from pydantic import Field
import uuid

class StockAdjustment(BaseModel):
    sku: str = Field(min_length=1, max_length=120)
    quantity_delta: float
    reason: str = Field(min_length=3, max_length=500)
    request_id: str = Field(min_length=8, max_length=120)
    job_number: str = Field(default="", max_length=120)
    reference: str = Field(default="", max_length=120)


def _sku(value):
    return str(value or '').strip().casefold()


def stock_snapshot(request):
    from app.routers.pds_purchase_orders import _receive_events
    catalog = ws.load(ws.location(request, 'doorks', 'inventory'))
    receiving = _receive_events(request, 'doorks')
    changes = ws.load(ws.location(request, 'doorks', 'stock_adjustments'))
    items = {}
    for part in catalog:
        sku = str(part.get('part_number') or part.get('sku') or '').strip()
        if not sku: continue
        key = _sku(sku)
        entry = items.setdefault(key, dict(sku=sku, description='', supplier='', unit_cost=0,
                                            received=0.0, adjustments=0.0, on_hand=0.0, catalog_id=''))
        entry.update(description=part.get('description',''), supplier=part.get('supplier',''),
                     unit_cost=part.get('unit_cost',0), catalog_id=part.get('id',''),
                     opening_quantity=float(part.get('quantity') or 0))
    for event in receiving:
        if not event.get('to_inventory') or not _sku(event.get('sku')): continue
        sku = str(event['sku']).strip(); key = _sku(sku)
        entry = items.setdefault(key, dict(sku=sku, description='', supplier='', unit_cost=0,
                                            received=0.0, adjustments=0.0, on_hand=0.0, catalog_id=''))
        entry['received'] += float(event.get('quantity') or 0)
    for change in changes:
        key = _sku(change.get('sku'))
        if not key: continue
        entry = items.setdefault(key, dict(sku=change['sku'], description='', supplier='', unit_cost=0,
                                            received=0.0, adjustments=0.0, on_hand=0.0, catalog_id=''))
        entry['adjustments'] += float(change.get('quantity_delta') or 0)
    for entry in items.values():
        entry['on_hand'] = round(float(entry.get('opening_quantity') or 0) + entry['received'] + entry['adjustments'], 4)
        entry['received'] = round(entry['received'], 4)
        entry['adjustments'] = round(entry['adjustments'], 4)
    return dict(items=sorted(items.values(), key=lambda x:x['sku'].casefold()),
                adjustment_count=len(changes), receipt_count=len(receiving),
                note='On-hand derives from receiving and recorded stock adjustments. No automatic usage deductions yet.')

@router.get('/stock')
def stock(request: Request):
    guard(request)
    return stock_snapshot(request)

@router.post('/stock/adjustments')
def adjust_stock(payload: StockAdjustment, request: Request):
    guard(request)
    from math import isfinite
    if not isfinite(payload.quantity_delta) or abs(payload.quantity_delta)>1000000 or payload.quantity_delta==0:
        raise HTTPException(400,'Enter a finite nonzero adjustment quantity')
    with _lock:
        path=ws.location(request,'doorks','stock_adjustments')
        changes=ws.load(path)
        previous=next((r for r in changes if r.get('request_id')==payload.request_id),None)
        if previous:
            if (_sku(previous['sku'])!=_sku(payload.sku) or float(previous['quantity_delta'])!=payload.quantity_delta
                or str(previous.get('job_number',''))!=payload.job_number.strip() or str(previous.get('reference',''))!=payload.reference.strip()):
                raise HTTPException(409,'Request ID reused for different stock adjustment')
            return dict(item=previous,duplicate=True)
        before=next((i for i in stock_snapshot(request)['items'] if _sku(i['sku'])==_sku(payload.sku)),None)
        if before is None:raise HTTPException(404,'Part number not found in catalog or receiving history')
        if before['on_hand']+payload.quantity_delta < -0.000001:
            raise HTTPException(409,'Adjustment would make on-hand quantity negative')
        record=dict(id=uuid.uuid4().hex,sku=before['sku'],quantity_delta=payload.quantity_delta,
                    reason=payload.reason.strip(),request_id=payload.request_id,
                    job_number=payload.job_number.strip(),reference=payload.reference.strip(),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    actor=str(request.state.auth_user.get('id','')))
        changes.append(record);ws.save(path,changes)
        return dict(item=record,duplicate=False,on_hand=round(before['on_hand']+payload.quantity_delta,4))

@router.get('/stock/adjustments')
def stock_adjustments(request: Request):
    """Read-only append-only stock movement journal; never modifies inventory."""
    guard(request)
    with _lock:
        rows = ws.load(ws.location(request, 'doorks', 'stock_adjustments'))
        return dict(items=list(reversed(rows[-500:])), total=len(rows))

@router.get('/financial-register')
def financial_register(request: Request):
    guard(request)
    from app.routers import accounting_ledger as ledger
    linked_bills=ac.read(ac.base(request)/'supplier_bills.json')
    manual_bills=ledger.load(ledger.path(request,'doorks','bills'))
    manual_payments=ledger.load(ledger.path(request,'doorks','payments'))
    events=ws.load(ac.base(request)/'workflow_events.json')
    ar=ac.read(ac.base(request)/'receivables.json')
    invoices=ws.load(ws.location(request,'doorks','estimates_invoices'))
    orders=ws.load(ws.location(request,'doorks','purchase_orders'))
    bills=[]
    for row in linked_bills:
        bills.append(dict(**row,origin='linked_workflow',supplier=row.get('vendor',''),
                          balance=round(float(row.get('amount') or 0)-float(row.get('paid') or 0),2)))
    for row in manual_bills:
        bills.append(dict(**row,origin='manual_ledger',balance=float(row.get('amount') or 0)))
    payment_events=[e for e in events if e.get('action') in ('payment_sent','payment_received')]
    return dict(supplier_bills=bills,manual_payments=manual_payments,workflow_payment_events=payment_events,
                receivables=ar,invoice_count=sum(str(d.get('document_type','')).lower()=='invoice' for d in invoices),
                purchase_order_count=len(orders),
                linked_supplier_balance=round(sum(max(0,float(b['balance'])) for b in bills if b['origin']=='linked_workflow'),2),
                manual_supplier_bill_total=round(sum(float(b.get('amount') or 0) for b in bills if b['origin']=='manual_ledger'),2),
                note='Linked and manual bills shown separately. No automatic merging or double-counting across sources.')
