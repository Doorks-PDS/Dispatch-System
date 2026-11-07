"""Doorks-only payroll calculation, employee access and financial reconciliation.

No external payroll submission, bank settlement or journal posting is performed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from threading import RLock
import json
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path
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


def effective_rate(employee, work_date):
    """Only documented effective-dated wages may be used for historical payroll."""
    history=employee.get('wage_history') or []
    valid=[h for h in history if isinstance(h,dict) and str(h.get('effective_date',''))<=str(work_date) and h.get('hourly_rate') not in (None,'')]
    if valid:
        return money(max(valid,key=lambda h:h['effective_date'])['hourly_rate'])
    return None

def card_rate(card, employee):
    # Approval freezes the rate even if the employee is later edited.
    if card.get('hourly_rate_snapshot') not in (None,''):
        return money(card['hourly_rate_snapshot'])
    return effective_rate(employee,str(card.get('work_date',''))) if employee else None

def card_gross(card, rate):
    return ((Decimal(str(card.get('regular_hours') or 0)) + Decimal(str(card.get('pto_hours') or 0)) + Decimal(str(card.get('holiday_hours') or 0)))*rate + Decimal(str(card.get('overtime_hours') or 0))*rate*Decimal('1.5')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)

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
                      calculation_version=1, hourly_rate_snapshot=float(effective_rate(employee,data.work_date)) if effective_rate(employee,data.work_date) is not None else None)
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
        row.update(hourly_rate_snapshot=float(effective_rate(employee,data.work_date)) if effective_rate(employee,data.work_date) is not None else None, employee_id=data.employee_id, employee=employee.get('name', ''), work_date=data.work_date,
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
        if data.approved and card_rate(row,next((e for e in staff(request) if e.get('id')==row.get('employee_id')),{})) is None:
            raise HTTPException(409,'Wage rate history missing for this work date; record and verify an effective-dated wage before approval')
        if data.approved and row.get('hourly_rate_snapshot') is None:
            row['hourly_rate_snapshot']=float(card_rate(row,next((e for e in staff(request) if e.get('id')==row.get('employee_id')),{})))
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
        rates=[card_rate(r,emp) for r in records]
        rate=rates[-1] if rates and all(v is not None for v in rates) and len(set(rates))==1 else None
        totals={k:sum(Decimal(str(r.get(k,0) or 0)) for r in records) for k in ('regular_hours','overtime_hours','pto_hours','holiday_hours')}
        pending=sum(r.get('supervisor_approved')!='Yes' or not r.get('calculation_version') for r in records)
        missing_rates=sum(v is None for v in rates)
        pto_bank = hours(emp.get('pto_bank', 0)) if emp else Decimal(0)
        pto_exceeds_bank = totals['pto_hours'] > pto_bank
        gross=sum((card_gross(r,v) for r,v in zip(records,rates) if v is not None),Decimal(0))
        output.append(dict(employee_id=employee_id,employee=emp.get('name') or records[0].get('employee',''),
                           hourly_rate=float(rate) if rate is not None else None, missing_wage_rates=missing_rates, **{k:float(v) for k,v in totals.items()},
                           pending_approval=pending, timecards=len(records),
                           estimated_gross=float(gross.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)),
                           pto_bank_hours=float(pto_bank), pto_exceeds_bank=pto_exceeds_bank,
                           ready_for_export=pending==0 and missing_rates==0 and bool(emp) and not pto_exceeds_bank))
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


# Rev65: audit-friendly source-data exports; these are NOT tax returns or payroll filings.
import csv, io
from fastapi.responses import StreamingResponse

def _csv_response(rows,headers,filename):
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=headers,extrasaction='ignore');writer.writeheader()
    for row in rows: writer.writerow({k:row.get(k,'') for k in headers})
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={
        'Content-Disposition':'attachment; filename="'+filename+'"',
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.get('/payroll/export')
def export_payroll(start:str,end:str,request:Request):
    report=pay_period(start,end,request)
    if any(not e['ready_for_export'] for e in report['employees']):
        raise HTTPException(409,'Approve all timecards and resolve PTO discrepancies before payroll export')
    headers=['employee_id','employee','hourly_rate','regular_hours','overtime_hours','pto_hours','holiday_hours',
             'timecards','pending_approval','estimated_gross','ready_for_export']
    return _csv_response(report['employees'],headers,'doorks-payroll-'+start+'-'+end+'.csv')

@router.get('/timecards/export')
def export_timecards(start:str,end:str,request:Request):
    pay_period(start,end,request) # date validation and permission check
    headers=['id','employee_id','employee','work_date','time_in','time_out','lunch_minutes','regular_hours',
             'overtime_hours','pto_hours','holiday_hours','supervisor_approved','notes']
    return _csv_response([r for r in cards(request) if start<=str(r.get('work_date',''))<=end],headers,
                         'doorks-timecards-'+start+'-'+end+'.csv')

@router.get('/payroll/diagnostics')
def payroll_diagnostics(start:str,end:str,request:Request):
    report=pay_period(start,end,request)
    rows=[r for r in cards(request) if start<=str(r.get('work_date',''))<=end]
    employees=report['employees']
    return {'period':{'start':start,'end':end},'employee_count':len(employees),
            'timecard_count':len(rows),'pending_approval':sum(e['pending_approval'] for e in employees),
            'regular_hours':round(sum(e['regular_hours'] for e in employees),2),
            'overtime_hours':round(sum(e['overtime_hours'] for e in employees),2),
            'double_time_hours':0.0, 'missing_wage_rates':sum(e['missing_wage_rates'] for e in employees),
            'pto_hours':round(sum(e['pto_hours'] for e in employees),2),
            'holiday_hours':round(sum(e['holiday_hours'] for e in employees),2),
            'estimated_gross':report['estimated_gross_total'],
            'export_ready':all(e['ready_for_export'] for e in employees) and bool(employees),
            'note':report['note']+' CSV exports are not W-2, 941, or other tax filings.'}

@router.get('/payroll/annual-export')
def annual_payroll_export(year:int,request:Request):
    guard(request)
    if year<2020 or year>2100:raise HTTPException(400,'Invalid tax year')
    first,last=f'{year}-01-01',f'{year}-12-31'
    employees={str(e.get('id')):e for e in staff(request)}
    totals=defaultdict(lambda:dict(regular_hours=Decimal(0),overtime_hours=Decimal(0),
        pto_hours=Decimal(0),holiday_hours=Decimal(0),timecards=0,unapproved=0))
    for card in cards(request):
        if not first<=str(card.get('work_date',''))<=last:continue
        employee_id=str(card.get('employee_id') or '')
        group=totals[employee_id]
        for key in ('regular_hours','overtime_hours','pto_hours','holiday_hours'):
            group[key]+=Decimal(str(card.get(key) or 0))
        group['timecards']+=1
        if card.get('supervisor_approved')!='Yes':group['unapproved']+=1
    rows=[]
    for eid,t in totals.items():
        emp=employees.get(eid,{})
        historical=[c for c in cards(request) if str(c.get('employee_id') or '')==eid and first<=str(c.get('work_date',''))<=last]
        rates=[card_rate(c,emp) for c in historical]
        missing=sum(r is None for r in rates)
        gross=sum((card_gross(c,r) for c,r in zip(historical,rates) if r is not None),Decimal(0))
        rows.append({'tax_year':year,'employee_id':eid,'employee':emp.get('name',''),
            'regular_hours':float(t['regular_hours']),'overtime_hours':float(t['overtime_hours']),
            'pto_hours':float(t['pto_hours']),'holiday_hours':float(t['holiday_hours']),
            'timecards':t['timecards'],'unapproved':t['unapproved'],
            'estimated_gross':float(gross.quantize(Decimal('0.01'))) if not missing else '', 'missing_wage_rates':missing,
            'report_type':'ESTIMATED SOURCE HOURS - NOT A TAX RETURN',
            'limitations':'Missing historical wage rates must be reconciled; withholding, deductions and taxes not verified'})
    headers=['tax_year','employee_id','employee','regular_hours','overtime_hours','pto_hours','holiday_hours',
             'timecards','unapproved','estimated_gross','missing_wage_rates','report_type','limitations']
    return _csv_response(rows,headers,f'doorks-annual-earnings-source-{year}.csv')

class VerifiedWage(BaseModel):
    effective_date: str
    hourly_rate: float
    evidence_note: str

@router.post('/employees/{employee_id}/verified-wage')
def record_verified_wage(employee_id:str, payload:VerifiedWage, request:Request):
    """Office-only wage history entry; no retrospective payroll recalculation or silent backfill."""
    guard(request)
    if getattr(request.state,'auth_role',None)!='office_admin':
        raise HTTPException(403,'Office Admin required')
    try: date.fromisoformat(payload.effective_date)
    except ValueError: raise HTTPException(422,'Effective date must be YYYY-MM-DD')
    rate=money(payload.hourly_rate)
    if len(payload.evidence_note.strip())<8:
        raise HTTPException(422,'Record payroll evidence or approval reference')
    with _lock:
        employees=staff(request)
        emp=next((e for e in employees if str(e.get('id'))==employee_id),None)
        if not emp:raise HTTPException(404,'Employee not found')
        history=list(emp.get('wage_history') or [])
        if any(x.get('effective_date')==payload.effective_date for x in history):
            raise HTTPException(409,'Existing rate on this date; investigate instead of overwriting')
        history.append({'effective_date':payload.effective_date,'hourly_rate':str(rate),
                        'evidence_note':payload.evidence_note.strip()[:500],
                        'recorded_at':datetime.now(timezone.utc).isoformat(),
                        'recorded_by':request.state.auth_user.get('id')})
        emp['wage_history']=sorted(history,key=lambda x:x['effective_date'])
        ws.save(ws.location(request,'doorks','employees'),employees)
    return {'ok':True,'effective_date':payload.effective_date,'hourly_rate':float(rate)}


# Revision 69: append-only, effective-dated PTO transactions and manual-payment allocation.
# Historical approvals and posted payment allocations are never silently recalculated.
class PTOEntry(BaseModel):
    employee_id: str
    effective_date: str
    entry_type: str  # opening, accrual_rate, adjustment
    hours: float
    note: str = ''

class PaymentAllocation(BaseModel):
    payment_id: str
    receivable_id: str


def _pto_path(request):
    return ws.location(request, 'doorks', 'pto_ledger')


def _pto_entries(request):
    return ws.load(_pto_path(request))


def _pto_decimal(value):
    try:
        result=Decimal(str(value))
        if not result.is_finite() or abs(result)>Decimal('100000'):
            raise ValueError()
        return result.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    except (ValueError,InvalidOperation,TypeError):
        raise HTTPException(400,'Invalid PTO hours')


def _pto_snapshot(entries, employee_id, through):
    relevant=sorted((x for x in entries if x.get('employee_id')==employee_id and x.get('effective_date','')<=through),key=lambda x:(x['effective_date'],x.get('created_at','')))
    balance=Decimal('0');rate=Decimal('0');last=None
    for row in relevant:
        kind=row['entry_type'];h=_pto_decimal(row['hours'])
        if kind=='opening': balance+=h
        elif kind=='adjustment': balance+=h
        elif kind=='accrual_rate': rate=h
        elif kind=='accrual': balance+=h
        elif kind=='usage': balance-=h
        last=row['effective_date']
    return {'employee_id':employee_id,'through':through,'balance_hours':float(balance),'accrual_hours_per_period':float(rate),'last_event_date':last}

@router.get('/pto-ledger')
def pto_ledger(request:Request, employee_id:str='', through:str=''):
    guard(request)
    end=through or date.today().isoformat()
    try:date.fromisoformat(end)
    except ValueError:raise HTTPException(400,'Invalid as-of date')
    employees=staff(request)
    entries=_pto_entries(request)
    if employee_id and not any(e.get('id')==employee_id for e in employees):raise HTTPException(404,'Employee not found')
    selected=[e for e in employees if not employee_id or e.get('id')==employee_id]
    return {'entries':[x for x in entries if not employee_id or x.get('employee_id')==employee_id], 'balances':[_pto_snapshot(entries,e.get('id'),end) for e in selected], 'note':'Accrual entries are explicitly posted for each pay period; changing an accrual rate does not rewrite prior entries.'}

@router.post('/pto-ledger')
def add_pto_entry(data:PTOEntry,request:Request):
    guard(request)
    if getattr(request.state,'auth_role',None)!='office_admin':raise HTTPException(403,'Office Admin required')
    if data.entry_type not in ('opening','accrual_rate','adjustment'):raise HTTPException(400,'Invalid PTO entry type')
    try:date.fromisoformat(data.effective_date)
    except ValueError:raise HTTPException(400,'Invalid effective date')
    h=_pto_decimal(data.hours)
    if data.entry_type=='accrual_rate' and h<0:raise HTTPException(400,'Accrual rate must be nonnegative')
    if not any(e.get('id')==data.employee_id for e in staff(request)):raise HTTPException(404,'Employee not found')
    import uuid
    with _lock:
        entries=_pto_entries(request)
        if data.entry_type=='opening' and any(e.get('employee_id')==data.employee_id and e.get('entry_type')=='opening' for e in entries):
            raise HTTPException(409,'Opening balance already exists; use an adjustment')
        entry={'id':uuid.uuid4().hex,'employee_id':data.employee_id,'effective_date':data.effective_date,'entry_type':data.entry_type,'hours':float(h),'note':data.note[:1000], 'created_at':datetime.now(timezone.utc).isoformat(),'created_by':str(request.state.auth_user.get('id',''))}
        entries.append(entry);ws.save(_pto_path(request),entries)
        return {'item':entry,'balance':_pto_snapshot(entries,data.employee_id,date.today().isoformat())}

class PTOAccrual(BaseModel):
    employee_id:str
    period_start:str
    period_end:str

@router.post('/pto-ledger/post-accrual')
def post_pto_accrual(data:PTOAccrual,request:Request):
    guard(request)
    if getattr(request.state,'auth_role',None)!='office_admin':raise HTTPException(403,'Office Admin required')
    try:first=date.fromisoformat(data.period_start);last=date.fromisoformat(data.period_end)
    except ValueError:raise HTTPException(400,'Invalid period dates')
    if first>last or (last-first).days>45:raise HTTPException(400,'Invalid pay period')
    if not any(e.get('id')==data.employee_id for e in staff(request)):raise HTTPException(404,'Employee not found')
    with _lock:
        entries=_pto_entries(request)
        if any(e.get('entry_type')=='accrual' and e.get('employee_id')==data.employee_id and e.get('period_start')==data.period_start and e.get('period_end')==data.period_end for e in entries):raise HTTPException(409,'Accrual already posted for this period')
        rate=_pto_decimal(_pto_snapshot(entries,data.employee_id,data.period_end)['accrual_hours_per_period'])
        import uuid
        item={'id':uuid.uuid4().hex,'employee_id':data.employee_id,'effective_date':data.period_end,'entry_type':'accrual','hours':float(rate),'period_start':data.period_start,'period_end':data.period_end,'created_at':datetime.now(timezone.utc).isoformat(),'created_by':str(request.state.auth_user.get('id',''))}
        entries.append(item);ws.save(_pto_path(request),entries)
        return {'item':item,'balance':_pto_snapshot(entries,data.employee_id,data.period_end)}

@router.get('/payment-reconciliation')
def payment_reconciliation(request:Request):
    guard(request)
    from app.routers import accounting_ledger as al
    from app.routers import doorks_accounting as accounting
    payments=[p for p in al.load(al.path(request,'doorks','payments')) if p.get('direction')=='received']
    receivables=accounting.read(accounting.base(request)/'receivables.json')
    allocations=ws.load(ws.location(request,'doorks','payment_allocations'))
    return {'payments':[dict(p,allocated=any(a.get('payment_id')==p.get('id') for a in allocations)) for p in payments], 'receivables':receivables,'allocations':allocations}

@router.post('/payment-reconciliation/allocate')
def allocate_payment(data:PaymentAllocation,request:Request):
    guard(request)
    from app.routers import accounting_ledger as al
    from app.routers import doorks_accounting as accounting
    from app.routers import doorks_workflow as workflow
    with _lock:
        payments=al.load(al.path(request,'doorks','payments'))
        payment=next((p for p in payments if p.get('id')==data.payment_id and p.get('direction')=='received'),None)
        if payment is None:raise HTTPException(404,'Received payment not found')
        allocation_path=ws.location(request,'doorks','payment_allocations')
        allocations=ws.load(allocation_path)
        if any(a.get('payment_id')==data.payment_id for a in allocations):raise HTTPException(409,'Payment already allocated; duplicate prevented')
        receivable_path=accounting.base(request)/'receivables.json'
        rows=accounting.read(receivable_path)
        invoice=next((r for r in rows if r.get('id')==data.receivable_id),None)
        if invoice is None:raise HTTPException(404,'Invoice receivable not found')
        amount=money(payment.get('amount'))
        remaining=money(invoice.get('amount'))-money(invoice.get('paid'))
        if amount<=0 or amount>remaining:raise HTTPException(409,'Payment exceeds invoice outstanding balance')
        ref=str(payment.get('reference_id','')).strip().casefold()
        invoice_ref=str(invoice.get('invoice_number','')).strip().casefold()
        if ref and invoice_ref and ref!=invoice_ref:
            raise HTTPException(409,'Payment reference does not match invoice number; correct the reference before allocation')
        import uuid
        allocation={'id':uuid.uuid4().hex,'payment_id':data.payment_id,'receivable_id':data.receivable_id,'invoice_number':invoice.get('invoice_number',''),'amount':float(amount),'allocated_at':datetime.now(timezone.utc).isoformat(),'allocated_by':str(request.state.auth_user.get('id',''))}
        # Persist allocation marker first to prevent replay after a retry; recovery must review
        # incomplete allocations rather than automatically duplicating a financial posting.
        allocation['status']='pending_post'
        allocations.append(allocation);ws.save(allocation_path,allocations)
        try:
            invoice['paid']=float((money(invoice.get('paid'))+amount).quantize(Decimal('.01')))
            invoice['status']='Paid' if money(invoice['paid'])>=money(invoice['amount']) else 'Partially Paid'
            invoice['updated_at']=datetime.now(timezone.utc).isoformat()
            accounting.write(receivable_path,rows)
        except Exception:
            raise HTTPException(500,'Allocation pending review; do not retry until reconciled')
        allocation['status']='posted';ws.save(allocation_path,allocations)
        return {'item':allocation,'receivable':invoice}

@router.get('/relationship-hubs')
def relationship_hubs(request:Request):
    guard(request)
    customers=ws.load(ws.location(request,'doorks','customers'))
    vendors=ws.load(ws.location(request,'doorks','vendors'))
    jobs=ws.load(ws.location(request,'doorks','work_orders'))
    docs=ws.load(ws.location(request,'doorks','estimates_invoices'))
    assignments=ws.load(ws.location(request,'doorks','vendor_assignments'))
    def match(row, entity):
        names=[str(entity.get(k,'')).strip().casefold() for k in ('name','customer','company','vendor','supplier')]
        names=[n for n in names if n]
        return any(str(row.get(k,'')).strip().casefold() in names for k in ('customer','customer_name','company','vendor','supplier') if row.get(k))
    def hub(items, vendor=False):
        return [dict(record=x,work_orders=[j for j in jobs if match(j,x)],documents=[d for d in docs if match(d,x)],assignments=[a for a in assignments if match(a,x)] if vendor else []) for x in items]
    return {'customers':hub(customers),'vendors':hub(vendors,True),'note':'Relationships match exact company names; review records with aliases or renamed companies.'}


# Workspace-specific settings live alongside the existing Doorks records.
# They do not change legacy PDS settings or overwrite existing documents.
class WorkspaceSettingsUpdate(BaseModel):
    settings: dict


def _settings_path(request: Request, scope: str):
    if scope not in ('business', 'accounting'):
        raise HTTPException(404, 'Unknown settings section')
    ws.guard(request, 'doorks', 'work_orders')
    return ws.location(request, 'doorks', 'work_orders').parent / ('settings_' + scope + '.json')


@router.get('/settings/{scope}')
def read_workspace_settings(scope: str, request: Request):
    path = _settings_path(request, scope)
    with _lock:
        if not path.exists():
            return {'settings': {}}
        try:
            settings = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise HTTPException(500, 'Stored settings could not be read') from exc
        if not isinstance(settings, dict):
            raise HTTPException(500, 'Invalid stored settings')
        return {'settings': settings}


@router.put('/settings/{scope}')
def update_workspace_settings(scope: str, payload: WorkspaceSettingsUpdate, request: Request):
    path = _settings_path(request, scope)
    if len(payload.settings) > 40:
        raise HTTPException(400, 'Too many settings')
    cleaned = {}
    for key, value in payload.settings.items():
        if not isinstance(key, str) or not key.replace('_', '').isalnum() or len(key) > 64:
            raise HTTPException(400, 'Invalid settings key')
        if not isinstance(value, str) or len(value) > 4000:
            raise HTTPException(400, 'Settings values must be text (maximum 4000 characters)')
        cleaned[key] = value
    with _lock:
        existing = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise HTTPException(500, 'Stored settings could not be read') from exc
            if not isinstance(existing, dict):
                raise HTTPException(500, 'Invalid stored settings')
        existing.update(cleaned)
        temp = path.with_name(path.name + '.tmp')
        try:
            with temp.open('w', encoding='utf-8') as output:
                json.dump(existing, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()
    return {'ok': True, 'settings': existing}

@router.get('/workflow-readiness')
def workflow_readiness(request: Request):
    """Read-only preflight for the end-to-end office workflow; never posts transactions."""
    guard(request)
    collections = ('customer_inquiries','work_orders','vendor_assignments',
                   'estimates_invoices','purchase_orders')
    counts = {kind:len(ws.load(ws.location(request,'doorks',kind))) for kind in collections}
    from app.routers import accounting_ledger as ledger
    counts['payments'] = len(ledger.load(ledger.path(request,'doorks','payments')))
    counts['supplier_bills'] = len(ac.read(ac.base(request)/'supplier_bills.json'))
    counts['receivables'] = len(ac.read(ac.base(request)/'receivables.json'))
    from app.routers.pds_purchase_orders import _receive_events
    counts['receiving_events'] = len(_receive_events(request,'doorks'))
    report = reconciliation(request)
    return {'ok':len(report['issues'])==0,
            'counts':counts,
            'reconciliation_issues':report['issues'],
            'stages':['Customer inquiry','Work order','Vendor assignment',
                      'Completion','Estimate','Invoice','Purchase order',
                      'Receiving','Supplier bill','Payment allocation'],
            'note':'Read-only inventory and accounting preflight; does not prove that a full browser workflow passed.'}

# Rev 115: read-only, job-scoped workflow trace. No automatic status changes or postings.
def _workflow_job_key(record):
    """Only explicit job references are trusted; customer names are not unique."""
    for field in ('job_number', 'work_order_number', 'job_no', 'jobNumber'):
        value = record.get(field)
        if value is not None and str(value).strip():
            return str(value).strip().casefold()
    return ''


def _workflow_trace_rows(job_number, records):
    """Summarize persisted links without claiming a step is complete from a count."""
    key = str(job_number).strip().casefold()
    if not key:
        raise HTTPException(400, 'Job number required')
    stages = {}
    for name, rows in records.items():
        matches = [row for row in rows if isinstance(row, dict) and _workflow_job_key(row) == key]
        stages[name] = {
            'count': len(matches),
            'records': [
                {'id': str(row.get('id') or ''),
                 'status': str(row.get('status') or ''),
                 'reference': str(row.get('document_number') or row.get('po_number') or row.get('invoice_number') or '')}
                for row in matches[:50]
            ],
            'truncated': len(matches) > 50,
        }
    return stages


def _workflow_completion_stage(job_number, work_orders):
    """Find actual completion forms embedded in explicitly linked work orders.

    Completion forms live on work-order records; they are not a separate
    workspace collection. A completed status alone is not proof of a form.
    """
    key = str(job_number).strip().casefold()
    matches = []
    for order in work_orders:
        if not isinstance(order, dict) or _workflow_job_key(order) != key:
            continue
        forms = order.get('completion_forms')
        if not isinstance(forms, list):
            continue
        for index, form in enumerate(forms):
            if not isinstance(form, dict) or not form:
                continue
            matches.append({
                'id': str(form.get('id') or ''),
                'status': str(form.get('status') or 'Saved'),
                'reference': str(order.get('job_number') or order.get('work_order_number') or ''),
                'work_order_id': str(order.get('id') or ''),
                'form_index': index,
            })
    unique = []
    seen = set()
    for item in matches:
        identity = (item['work_order_id'] or item['reference'].casefold(),
                    item['id'] or str(item['form_index']))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(item)
    return {'count': len(unique), 'records': unique[:50], 'truncated': len(unique) > 50}


@router.get('/workflow-trace/{job_number}')
def workflow_trace(job_number: str, request: Request):
    """Inspect explicitly linked Doorks records for a job; does not write or infer payment."""
    guard(request)
    if not job_number.strip() or len(job_number) > 80:
        raise HTTPException(400, 'Invalid job number')
    collections = ('customer_inquiries', 'work_orders', 'vendor_assignments',
                   'estimates_invoices', 'purchase_orders')
    records = {kind: ws.load(ws.location(request, 'doorks', kind)) for kind in collections}
    records['receivables'] = ac.read(ac.base(request) / 'receivables.json')
    records['supplier_bills'] = ac.read(ac.base(request) / 'supplier_bills.json')
    # Receiving journal references PO IDs, not job numbers. Resolve only through
    # purchase orders explicitly linked to this job; never match by customer name.
    from app.routers.pds_purchase_orders import _receive_events
    from app.routers import accounting_ledger as ledger
    receiving = _receive_events(request, 'doorks')
    payments = ledger.load(ledger.path(request, 'doorks', 'payments'))
    stages = _workflow_trace_rows(job_number, records)
    # Dispatch completion forms are persisted by CalendarStore, not necessarily
    # in the separate Doorks workspace work_orders collection. Read the actual
    # dispatch record first, retaining workspace forms for older installations.
    dispatch_store = getattr(request.app.state, 'calendar_store', None)
    dispatch_job = None
    if dispatch_store is not None:
        dispatch_job = dispatch_store.get_by_job_number(job_number.strip())
    completion_sources = list(records['work_orders'])
    if isinstance(dispatch_job, dict):
        completion_sources.append(dispatch_job)
        # The dispatch calendar is the canonical job store for older Doorks
        # work orders. Include it in the review without double-counting a
        # workspace record that references the same underlying job.
        existing_ids = {str(row.get('id') or '').strip() for row in records['work_orders']
                        if isinstance(row, dict) and row.get('id')}
        dispatch_id = str(dispatch_job.get('id') or '').strip()
        if not dispatch_id or dispatch_id not in existing_ids:
            work_order_stage = stages['work_orders']
            work_order_stage['count'] += 1
            if len(work_order_stage['records']) < 50:
                work_order_stage['records'].append({
                    'id': dispatch_id,
                    'status': str(dispatch_job.get('status') or ''),
                    'reference': str(dispatch_job.get('job_number') or job_number.strip()),
                })
            else:
                work_order_stage['truncated'] = True
    stages['completion_forms'] = _workflow_completion_stage(job_number, completion_sources)
    stages['receiving_events'] = _workflow_linked_receipts(
        job_number, records['purchase_orders'], receiving)
    stages['payments'] = _workflow_trace_rows(job_number, {'payments': payments})['payments']
    stages.update(_workflow_document_stages(job_number, records['estimates_invoices']))
    allocations = ws.load(ws.location(request, 'doorks', 'payment_allocations'))
    financial = _workflow_financial_reconciliation(
        job_number, records['estimates_invoices'], records['receivables'],
        records['supplier_bills'], payments, allocations)
    receiving_balances = _workflow_receiving_balances(job_number, records['purchase_orders'], receiving)
    return {
        'job_number': job_number.strip(), 'stages': stages,
        'receiving_balances': receiving_balances,
        'financial_reconciliation': financial,
        'linked_record_count': sum(stage['count'] for stage in stages.values()),
        'note': ('Only explicit job references and receiving events linked through '
                 'job-linked purchase order IDs are included. Payment entries are '
                 'manual/unverified and are not evidence of bank settlement. '
                 'Missing links do not prove a transaction is absent.'),
        'read_only': True,
    }


def _unique_po_ids(purchase_orders):
    """Only globally unique persisted PO IDs can safely attribute receiving."""
    counts = defaultdict(int)
    for po in purchase_orders:
        if isinstance(po, dict):
            po_id = str(po.get('id') or '').strip()
            if po_id:
                counts[po_id] += 1
    return {po_id for po_id, count in counts.items() if count == 1}


def _workflow_linked_receipts(job_number, purchase_orders, events):
    """Resolve PO receiving by stable PO ID; never guess using supplier/customer."""
    key = str(job_number).strip().casefold()
    unique_ids = _unique_po_ids(purchase_orders)
    linked_ids = {str(po.get('id') or '').strip() for po in purchase_orders
                  if isinstance(po, dict) and _workflow_job_key(po) == key
                  and str(po.get('id') or '').strip() in unique_ids}
    matches = [event for event in events if isinstance(event, dict)
               and str(event.get('po_id') or '') in linked_ids]
    return {'count': len(matches), 'records': [
        {'id': str(event.get('id') or ''),
         'status': 'Recorded receipt (not invoice/payment confirmation)',
         'reference': str(event.get('po_number') or event.get('reference') or '')}
        for event in matches[:50]], 'truncated': len(matches) > 50}


def _workflow_document_stages(job_number, documents):
    """Separate estimates from invoices; never count an estimate as an invoice."""
    key = str(job_number).strip().casefold()
    stages = {}
    for kind in ('estimate', 'invoice'):
        rows = [row for row in documents if isinstance(row, dict)
                and _workflow_job_key(row) == key
                and str(row.get('document_type') or '').strip().casefold() == kind]
        stages[kind + 's'] = {
            'count': len(rows),
            'records': [{'id': str(row.get('id') or ''),
                         'status': str(row.get('status') or ''),
                         'reference': str(row.get('document_number') or '')}
                        for row in rows[:50]],
            'truncated': len(rows) > 50,
        }
    return stages


def _workflow_receiving_balances(job_number, purchase_orders, events):
    """Summarize receiving by explicit PO IDs; flag invalid quantities for review."""
    key = str(job_number).strip().casefold()
    orders = [row for row in purchase_orders if isinstance(row, dict)
              and _workflow_job_key(row) == key]
    results = []
    unique_ids = _unique_po_ids(purchase_orders)
    for po in orders:
        po_id = str(po.get('id') or '').strip()
        if not po_id:
            results.append({'po_id': '', 'po_number': str(po.get('po_number') or ''),
                            'status': 'Needs Review', 'reason': 'Missing purchase order ID'})
            continue
        if po_id not in unique_ids:
            results.append({'po_id': po_id, 'po_number': str(po.get('po_number') or ''),
                            'status': 'Needs Review', 'reason': 'Duplicate purchase order ID; receiving attribution withheld'})
            continue
        linked = [e for e in events if isinstance(e, dict)
                  and str(e.get('po_id') or '') == po_id]
        try:
            ordered = Decimal(str(po.get('quantity') or 0))
            # Validate every receipt independently. A negative event must not be
            # hidden by a positive event in the aggregate, and non-finite values
            # must never enter a reconciliation balance.
            quantities = [Decimal(str(e.get('quantity') if e.get('quantity') is not None else 0))
                          for e in linked]
            if any(not q.is_finite() or q <= 0 for q in quantities):
                raise ValueError('Invalid receipt quantity')
            # A repeated persisted receipt ID can indicate duplicate posting.
            # Withhold the balance instead of double-counting it.
            event_ids = [str(e.get('id')).strip() for e in linked if e.get('id') is not None and str(e.get('id')).strip()]
            if len(event_ids) != len(set(event_ids)):
                raise ValueError('Duplicate receipt event ID')
            received = sum(quantities, Decimal(0))
            if not ordered.is_finite() or received < 0:
                raise ValueError('Invalid quantity')
            if ordered <= 0:
                raise ValueError('Nonpositive quantity')
            status = ('Over Received' if received > ordered else
                      'Received' if received == ordered else
                      'Partially Received' if received else 'Not Received')
            results.append({'po_id': po_id, 'po_number': str(po.get('po_number') or ''),
                            'ordered': float(ordered), 'received': float(received),
                            'outstanding': float(max(Decimal(0), ordered - received)),
                            'status': status})
        except (HTTPException, InvalidOperation, ValueError, TypeError):
            results.append({'po_id': po_id, 'po_number': str(po.get('po_number') or ''),
                            'status': 'Needs Review', 'reason': 'Invalid PO quantity, receipt quantity, or duplicate receipt ID'})
    return results




def _workflow_financial_reconciliation(job_number, documents, receivables, supplier_bills,
                                       payments, allocations):
    """Read-only financial linkage report; never infer a payment from customer names.

    Match receivables only by invoice number on a job-linked invoice, and
    allocations only by stable receivable/payment IDs. A missing identifier
    is an exception for manual review, not permission to guess.
    """
    key = str(job_number).strip().casefold()
    invoices = [d for d in documents if isinstance(d, dict)
                and _workflow_job_key(d) == key
                and str(d.get('document_type') or '').strip().casefold() == 'invoice']
    invoice_numbers = {str(d.get('document_number') or '').strip().casefold()
                       for d in invoices if str(d.get('document_number') or '').strip()}
    # A reused invoice number on another job makes receivable attribution ambiguous.
    # Do not assign those receivables to either job based on the number alone.
    other_job_numbers = {str(d.get('document_number') or '').strip().casefold()
                         for d in documents if isinstance(d, dict)
                         and str(d.get('document_type') or '').strip().casefold() == 'invoice'
                         and _workflow_job_key(d) != key
                         and str(d.get('document_number') or '').strip()}
    ambiguous_numbers = invoice_numbers & other_job_numbers
    safe_numbers = invoice_numbers - ambiguous_numbers
    linked_ar = [r for r in receivables if isinstance(r, dict)
                 and str(r.get('invoice_number') or '').strip().casefold() in safe_numbers
                 and str(r.get('invoice_number') or '').strip()]
    # Multiple receivables for the same invoice cannot safely be treated as
    # separate balances. Withhold them until the duplicate is resolved.
    ar_number_counts = defaultdict(int)
    for row in receivables:
        if isinstance(row, dict):
            number = str(row.get('invoice_number') or '').strip().casefold()
            if number in safe_numbers:
                ar_number_counts[number] += 1
    duplicate_ar_numbers = {n for n, count in ar_number_counts.items() if count > 1}
    linked_ar = [r for r in linked_ar
                 if str(r.get('invoice_number') or '').strip().casefold() not in duplicate_ar_numbers]
    ar_ids = {str(r.get('id')) for r in linked_ar if r.get('id')}
    linked_allocations = [a for a in allocations if isinstance(a, dict)
                          and str(a.get('receivable_id') or '') in ar_ids]
    payment_ids = {str(p.get('id')) for p in payments if isinstance(p, dict)
                   and str(p.get('direction') or '').casefold() == 'received' and p.get('id')}
    problems = []
    if ambiguous_numbers:
        problems.append('Invoice number also used on another job; receivable matching withheld for safety')
    if duplicate_ar_numbers:
        problems.append('Multiple receivables share an invoice number; matching withheld for safety')
    if invoices and len(invoice_numbers) != len(invoices):
        problems.append('Invoice missing number or duplicate invoice number')
    if invoices and not linked_ar:
        problems.append('No receivable explicitly matched to job invoice number')
    payment_by_id = {str(p['id']): p for p in payments if isinstance(p, dict)
                     and p.get('id') and str(p.get('direction') or '').casefold() == 'received'}
    posted_by_payment = defaultdict(list)
    posted_by_receivable = defaultdict(Decimal)
    for a in linked_allocations:
        payment_id = str(a.get('payment_id') or '')
        if payment_id not in payment_ids:
            problems.append('Allocation references missing received payment')
        if a.get('status') != 'posted':
            problems.append('Allocation not confirmed posted; manual review required')
            continue
        posted_by_payment[payment_id].append(a)
        if a.get('amount') in (None, ''):
            # Older allocations may lack a stored amount; do not infer zero.
            continue
        try:
            allocated = money(a.get('amount'))
            if allocated <= 0:
                problems.append('Posted allocation has zero amount')
            posted_by_receivable[str(a.get('receivable_id'))] += allocated
            if payment_id in payment_by_id and allocated > money(payment_by_id[payment_id].get('amount')):
                problems.append('Posted allocation exceeds received payment amount')
        except HTTPException:
            problems.append('Invalid posted allocation amount')
    if any(len(rows) > 1 for rows in posted_by_payment.values()):
        problems.append('Received payment has multiple posted allocations; review for duplicate posting')
    for r in linked_ar:
        try:
            amount, paid = money(r.get('amount')), money(r.get('paid'))
            if paid > amount:
                problems.append('Receivable paid amount exceeds invoice amount')
            if posted_by_receivable.get(str(r.get('id')), Decimal(0)) > amount:
                problems.append('Posted allocations exceed receivable invoice amount')
            if posted_by_receivable.get(str(r.get('id')), Decimal(0)) > paid:
                problems.append('Posted allocations exceed receivable recorded paid balance')
        except HTTPException:
            problems.append('Invalid receivable amount')
    bills = [b for b in supplier_bills if isinstance(b, dict)
             and _workflow_job_key(b) == key]
    return {'invoice_count': len(invoices), 'matched_receivable_count': len(linked_ar),
            'posted_allocation_count': sum(a.get('status') == 'posted' for a in linked_allocations),
            'supplier_bill_count': len(bills), 'issues': sorted(set(problems)),
            'read_only': True,
            'note': 'Payment allocation is not proof of bank settlement. Supplier bills are linked only by explicit job reference.'}

@router.get('/workflow-handoffs/{job_number}')
def workflow_handoffs(job_number: str, request: Request):
    """Read-only visibility of missing job links, not a transaction processor."""
    trace = workflow_trace(job_number, request)
    stages = trace['stages']
    checks = []
    for name, description in (
        ('work_orders', 'Work order'),
        ('vendor_assignments', 'Vendor assignment'),
        ('completion_forms', 'Saved completion form'),
        ('estimates', 'Estimate record'),
        ('invoices', 'Invoice record'),
        ('purchase_orders', 'Purchase order'),
        ('receiving_events', 'PO-linked receiving event'),
        ('supplier_bills', 'Supplier bill'),
        ('payments', 'Job-linked payment entry'),
    ):
        count = stages.get(name, {}).get('count', 0)
        checks.append({'stage': name, 'label': description,
                       'linked_records': count, 'has_explicit_link': count > 0})
    return {'job_number': trace['job_number'], 'checks': checks,
            'receiving_balances': trace['receiving_balances'],
            'financial_reconciliation': trace['financial_reconciliation'],
            'missing_explicit_links': [c['stage'] for c in checks if not c['has_explicit_link']],
            'read_only': True,
            'note': ('A missing explicit link does not mean a step is required or incomplete. '
                     'Payments are not proof of bank settlement. Estimates and invoices '
                     'are counted separately by document type.')}


@router.get('/workflow-review')
def workflow_review_page(request: Request):
    """Protected read-only job reconciliation screen on the existing Doorks service."""
    guard(request)
    root = Path(getattr(request.app.state, 'project_root', Path(__file__).resolve().parents[2]))
    return FileResponse(root / 'static' / 'doorks_workflow_review.html', media_type='text/html')
