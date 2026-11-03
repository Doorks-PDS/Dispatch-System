"""Doorks-only cross-hub workflows; no PDS or SDC data is modified."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.routers import workspaces as ws, doorks_accounting as ac

router = APIRouter(prefix='/doorks-workflow', tags=['doorks-workflow'])
lock = RLock()
class Money(BaseModel):
    amount: float
    reference: str = ''
class Receiving(BaseModel):
    quantity: float
    reference: str = ''
class SupplierBill(BaseModel):
    bill_number: str
    amount: float
    due_date: str = ''

def guard(request):
    ws.guard(request, 'doorks', 'estimates_invoices')
    ac.guard(request, 'receivables')
def amt(value):
    try:
        n = Decimal(str(value)).quantize(Decimal('.01'))
        if not n.is_finite() or n < 0 or n > 999999999: raise ValueError()
        return float(n)
    except (InvalidOperation, ValueError, TypeError): raise HTTPException(400, 'Invalid nonnegative amount')
def stamp(): return datetime.now(timezone.utc).isoformat()
def get(rows, id):
    row = next((r for r in rows if r.get('id') == id), None)
    if not row: raise HTTPException(404, 'Record not found')
    return row
def event(request, kind, source, action, value, reference=''):
    path = ac.base(request) / 'workflow_events.json'
    rows = ws.load(path)
    user = getattr(request.state, 'auth_user', None)
    actor = str(user.get('name') or user.get('username') or 'Admin') if isinstance(user, dict) else 'Admin'
    record = dict(id=uuid.uuid4().hex, kind=kind, source_id=source, action=action, amount=value, reference=reference[:120], actor=actor, created_at=stamp())
    rows.append(record); ws.save(path, rows)
    return record

@router.get('/overview')
def overview(request: Request):
    guard(request)
    with lock:
        docs = ws.load(ws.location(request, 'doorks', 'estimates_invoices'))
        ar = ac.read(ac.base(request) / 'receivables.json')
        po = ws.load(ws.location(request, 'doorks', 'purchase_orders'))
        ap = ac.read(ac.base(request) / 'supplier_bills.json')
        return dict(invoices=sum(str(d.get('document_type', '')).lower() == 'invoice' for d in docs), receivables=len(ar), open_ar=round(sum(max(0, amt(r.get('amount',0))-amt(r.get('paid',0))) for r in ar),2), purchase_orders=len(po), supplier_bills=len(ap), open_ap=round(sum(max(0, amt(r.get('amount',0))-amt(r.get('paid',0))) for r in ap),2))

@router.post('/invoices/{id}/sync-receivable')
def sync_invoice(id: str, request: Request):
    guard(request)
    with lock:
        invoice = get(ws.load(ws.location(request, 'doorks', 'estimates_invoices')), id)
        if str(invoice.get('document_type','')).lower() != 'invoice': raise HTTPException(400, 'Not an invoice')
        path = ac.base(request) / 'receivables.json'; rows = ac.read(path)
        existing = next((r for r in rows if r.get('source_invoice_id') == id), None)
        if existing: return dict(item=existing, already_exists=True)
        total = amt(invoice.get('total') or invoice.get('amount') or 0)
        paid = amt(invoice.get('paid') or 0)
        record = dict(id=uuid.uuid4().hex, source_invoice_id=id, invoice_number=str(invoice.get('document_number','')), customer=str(invoice.get('customer') or invoice.get('customer_name') or ''), job_number=str(invoice.get('work_order_number') or invoice.get('job_number') or ''), amount=total, paid=paid, status='Paid' if paid >= total else 'Open', created_at=stamp())
        rows.append(record); ac.write(path, rows); event(request,'invoice',id,'receivable_created',total)
        return dict(item=record, already_exists=False)

@router.post('/receivables/{id}/payments')
def customer_payment(id: str, data: Money, request: Request):
    guard(request); amount = amt(data.amount)
    if amount <= 0: raise HTTPException(400, 'Payment must be positive')
    with lock:
        path = ac.base(request) / 'receivables.json'; rows = ac.read(path); row = get(rows,id)
        if amount > round(amt(row.get('amount',0))-amt(row.get('paid',0)),2): raise HTTPException(409, 'Payment exceeds balance')
        record = event(request,'receivable',id,'payment_received',amount,data.reference)
        row['paid'] = round(amt(row.get('paid',0))+amount,2); row['status'] = 'Paid' if row['paid'] >= amt(row.get('amount',0)) else 'Partially Paid'; row['updated_at'] = stamp()
        ac.write(path,rows); return dict(item=row,event=record)

@router.post('/purchase-orders/{id}/receive')
def receive(id: str, data: Receiving, request: Request):
    guard(request); quantity = amt(data.quantity)
    if quantity <= 0: raise HTTPException(400, 'Quantity must be positive')
    with lock:
        path = ws.location(request,'doorks','purchase_orders'); rows = ws.load(path); row = get(rows,id)
        ordered = amt(row.get('quantity',0)); received = amt(row.get('received_quantity',0))
        if ordered <= 0 or received + quantity > ordered: raise HTTPException(409, 'Quantity exceeds remaining order')
        record = event(request,'purchase_order',id,'goods_received',quantity,data.reference)
        row['received_quantity'] = round(received+quantity,2); row['status'] = 'Received' if row['received_quantity'] >= ordered else 'Partially Received'; row['updated_at'] = stamp()
        ws.save(path,rows); return dict(item=row,event=record)

@router.get('/supplier-bills')
def bills(request: Request):
    guard(request); return dict(items=list(reversed(ac.read(ac.base(request)/'supplier_bills.json'))))

@router.post('/purchase-orders/{id}/supplier-bill')
def bill(id: str, data: SupplierBill, request: Request):
    guard(request); amount = amt(data.amount)
    if not data.bill_number.strip(): raise HTTPException(400,'Bill number required')
    with lock:
        po = get(ws.load(ws.location(request,'doorks','purchase_orders')),id)
        path = ac.base(request)/'supplier_bills.json'; rows = ac.read(path)
        existing = next((r for r in rows if r.get('source_po_id') == id and r.get('bill_number') == data.bill_number.strip()),None)
        if existing: return dict(item=existing,already_exists=True)
        record = dict(id=uuid.uuid4().hex,source_po_id=id,po_number=str(po.get('po_number','')),vendor=str(po.get('vendor') or po.get('supplier') or ''),bill_number=data.bill_number.strip()[:120],amount=amount,paid=0,status='Open',due_date=data.due_date[:40],created_at=stamp())
        rows.append(record); ac.write(path,rows); event(request,'purchase_order',id,'supplier_bill_created',amount,data.bill_number)
        return dict(item=record,already_exists=False)

@router.post('/supplier-bills/{id}/payments')
def supplier_payment(id: str, data: Money, request: Request):
    guard(request); amount = amt(data.amount)
    if amount <= 0: raise HTTPException(400,'Payment must be positive')
    with lock:
        path = ac.base(request)/'supplier_bills.json'; rows = ac.read(path); row = get(rows,id)
        if amount > round(amt(row.get('amount',0))-amt(row.get('paid',0)),2): raise HTTPException(409,'Payment exceeds balance')
        record = event(request,'supplier_bill',id,'payment_sent',amount,data.reference)
        row['paid'] = round(amt(row.get('paid',0))+amount,2); row['status'] = 'Paid' if row['paid'] >= amt(row.get('amount',0)) else 'Partially Paid'; row['updated_at'] = stamp()
        ac.write(path,rows); return dict(item=row,event=record)
