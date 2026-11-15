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
    from app.services.doorks_po_lock import po_write_lock
    with po_write_lock(request, 'doorks'), lock:
        path = ws.location(request,'doorks','purchase_orders'); rows = ws.load(path); row = get(rows,id)
        # Rev95: The older PO field and newer append-only journal are separate
        # representations. Never let this legacy endpoint ignore journal receipts.
        from app.routers import pds_purchase_orders as po_store
        if any(str(e.get('po_id')) == id for e in po_store._receive_events(request, 'doorks')):
            raise HTTPException(409, 'This PO has journal receipts; use journal receiving and review the legacy balance')
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
    from app.services.doorks_supplier_bill_lock import supplier_bill_lock
    with supplier_bill_lock(request):
        po = get(ws.load(ws.location(request,'doorks','purchase_orders')),id)
        path = ac.base(request)/'supplier_bills.json'; rows = ac.read(path)
        existing = next((r for r in rows if r.get('source_po_id') == id and r.get('bill_number') == data.bill_number.strip()),None)
        if existing: return dict(item=existing,already_exists=True)
        record = dict(id=uuid.uuid4().hex,source_po_id=id,po_number=str(po.get('po_number','')),vendor=str(po.get('vendor') or po.get('supplier') or ''),bill_number=data.bill_number.strip()[:120],amount=amount,paid=0,status='Open',due_date=data.due_date[:40],created_at=stamp())
        rows.append(record); ac.write(path,rows); event(request,'purchase_order',id,'supplier_bill_created',amount,data.bill_number)
        return dict(item=record,already_exists=False)

def _supplier_payment_events(events, bill_id):
    return [e for e in events if e.get('kind') == 'supplier_bill' and
            str(e.get('source_id', '')) == str(bill_id) and e.get('action') == 'payment_sent']


def _append_payment_mirror(request, entry, events, history_path):
    """Mirror an already-committed bill entry; never re-post its balance."""
    if any(str(e.get('id', '')) == entry['id'] for e in events):
        return next(e for e in events if str(e.get('id', '')) == entry['id'])
    mirror = dict(id=entry['id'], kind='supplier_bill', source_id=entry['bill_id'],
                  action='payment_sent', amount=entry['amount'], reference=entry['reference'],
                  actor=entry['actor'], created_at=entry['created_at'])
    events.append(mirror)
    ac.write(history_path, events)
    return mirror


@router.post('/supplier-bills/{id}/payments')
def supplier_payment(id: str, data: Money, request: Request):
    """Record a *manual* payment with an in-bill durable receipt and recoverable event.

    This never sends funds. Reference is the idempotency key within one bill.
    An inconsistent historical ledger blocks new payments until reviewed.
    """
    guard(request)
    amount = amt(data.amount)
    reference = data.reference.strip()
    if amount <= 0: raise HTTPException(400, 'Payment must be positive')
    if not reference or len(reference) > 120:
        raise HTTPException(400, 'Unique payment reference is required')
    from app.services.doorks_supplier_bill_lock import supplier_bill_lock
    with supplier_bill_lock(request):
        folder = ac.base(request)
        path = folder / 'supplier_bills.json'
        history_path = folder / 'workflow_events.json'
        rows = ac.read(path)
        row = get(rows, id)
        events = ac.read(history_path)
        matching = _supplier_payment_events(events, id)
        entries = row.get('moses_payment_entries', [])
        if not isinstance(entries, list):
            raise HTTPException(409, 'Invalid payment journal; review required')
        # Existing, committed entries are authoritative if their balance is intact.
        embedded_sum = Decimal('0')
        for item in entries:
            if not isinstance(item, dict):
                raise HTTPException(409, 'Invalid payment journal; review required')
            embedded_sum += Decimal(str(amt(item.get('amount', -1))))
        event_sum = sum((Decimal(str(amt(e.get('amount', -1)))) for e in matching), Decimal('0'))
        paid = Decimal(str(amt(row.get('paid', 0))))
        if paid != event_sum + sum((Decimal(str(amt(e.get('amount', 0)))) for e in entries
                                     if not any(str(x.get('id', '')) == str(e.get('id', '')) for x in matching)), Decimal('0')):
            raise HTTPException(409, 'Supplier payment history does not match bill balance; manual review required')
        refs = [str(e.get('reference', '')).strip().casefold() for e in matching]
        refs.extend(str(e.get('reference', '')).strip().casefold() for e in entries
                    if not any(str(x.get('id', '')) == str(e.get('id', '')) for x in matching))
        if any(not r for r in refs) or len(refs) != len(set(refs)):
            raise HTTPException(409, 'Ambiguous existing payment references; manual review required')
        key = reference.casefold()
        previous = next((e for e in entries if str(e.get('reference', '')).strip().casefold() == key), None)
        if previous:
            if amt(previous['amount']) != amount:
                raise HTTPException(409, 'Reference already used for a different amount')
            # A crash after the bill's atomic write can be healed without a second payment.
            mirror = _append_payment_mirror(request, previous, events, history_path)
            return dict(item=row, event=mirror, already_exists=True)
        if key in refs:
            raise HTTPException(409, 'Payment reference already recorded; no duplicate posting')
        if any(not any(str(x.get('id', '')) == str(e.get('id', '')) for x in matching) for e in entries):
            raise HTTPException(409, 'Unmirrored payment exists; retry its reference or review before posting a new payment')
        total = Decimal(str(amt(row.get('amount', 0))))
        if paid + Decimal(str(amount)) > total:
            raise HTTPException(409, 'Payment exceeds balance')
        user = getattr(request.state, 'auth_user', None)
        actor = str(user.get('name') or user.get('username') or 'Admin') if isinstance(user, dict) else 'Admin'
        entry = dict(id=uuid.uuid4().hex, bill_id=id, amount=amount, reference=reference,
                     actor=actor, created_at=stamp())
        row['moses_payment_entries'] = [*entries, entry]
        row['paid'] = float(paid + Decimal(str(amount)))
        row['status'] = 'Paid' if Decimal(str(row['paid'])) >= total else 'Partially Paid'
        row['updated_at'] = stamp()
        # This is the authoritative commit: bill balance and payment ID together.
        ac.write(path, rows)
        # The secondary event can be safely rebuilt on an identical retry.
        mirror = _append_payment_mirror(request, entry, events, history_path)
        return dict(item=row, event=mirror, already_exists=False)

@router.get('/reconciliation')
def reconciliation(request: Request):
    """Read-only, Doorks-scoped cross-record audit. Never silently creates or alters records."""
    guard(request)
    with lock:
        docs = ws.load(ws.location(request, 'doorks', 'estimates_invoices'))
        orders = ws.load(ws.location(request, 'doorks', 'purchase_orders'))
        jobs = ws.load(ws.location(request, 'doorks', 'work_orders'))
        receivables = ac.read(ac.base(request) / 'receivables.json')
        bills = ac.read(ac.base(request) / 'supplier_bills.json')
        events = ws.load(ac.base(request) / 'workflow_events.json')
        issues = []
        def flag(kind, record, code, message):
            issues.append(dict(kind=kind, id=str(record.get('id','')), number=str(record.get('document_number') or record.get('po_number') or record.get('bill_number') or record.get('job_number') or ''), code=code, message=message))
        ar_by_invoice = {}
        for r in receivables:
            source = str(r.get('source_invoice_id') or '')
            if source: ar_by_invoice.setdefault(source, []).append(r)
            if amt(r.get('paid',0)) > amt(r.get('amount',0)):
                flag('receivable',r,'overpaid','Recorded customer payments exceed invoice balance')
        ap_by_po = {}
        for b in bills:
            source = str(b.get('source_po_id') or '')
            if source: ap_by_po.setdefault(source, []).append(b)
            if amt(b.get('paid',0)) > amt(b.get('amount',0)):
                flag('supplier_bill',b,'overpaid','Recorded supplier payments exceed bill total')
        for d in docs:
            if str(d.get('document_type','')).lower() == 'invoice':
                links = ar_by_invoice.get(str(d.get('id','')), [])
                if not links: flag('invoice',d,'missing_receivable','Invoice has no linked customer balance; use Link to Customer Balance')
                if len(links)>1: flag('invoice',d,'duplicate_receivable','Multiple customer balances reference this invoice')
                for r in links:
                    if abs(amt(d.get('total') or d.get('amount') or 0)-amt(r.get('amount',0))) > .01:
                        flag('invoice',d,'total_mismatch','Invoice total differs from linked customer balance; manual review required')
        doc_ids = {str(d.get('id','')) for d in docs}
        po_ids = {str(p.get('id','')) for p in orders}
        for r in receivables:
            if r.get('source_invoice_id') and str(r['source_invoice_id']) not in doc_ids:
                flag('receivable',r,'orphan_invoice','Linked invoice is missing')
        for b in bills:
            if b.get('source_po_id') and str(b['source_po_id']) not in po_ids:
                flag('supplier_bill',b,'orphan_purchase_order','Linked purchase order is missing')
        for p in orders:
            ordered = amt(p.get('quantity',0)); received = amt(p.get('received_quantity',0))
            if received > ordered: flag('purchase_order',p,'over_received','Received quantity exceeds ordered quantity')
            if received > 0 and not ap_by_po.get(str(p.get('id',''))):
                flag('purchase_order',p,'received_unbilled','Goods received but no supplier bill linked')
        job_numbers = {str(j.get('job_number') or j.get('work_order_number') or '') for j in jobs}
        for d in docs:
            job_number = str(d.get('work_order_number') or d.get('job_number') or '')
            if job_number and job_number not in job_numbers:
                flag('document',d,'job_not_found','Referenced Doorks work order was not found')
        return dict(summary=dict(estimates=sum(str(d.get('document_type','')).lower()=='estimate' for d in docs), invoices=sum(str(d.get('document_type','')).lower()=='invoice' for d in docs), work_orders=len(jobs), purchase_orders=len(orders), receivables=len(receivables), supplier_bills=len(bills), workflow_events=len(events), open_customer_balance=round(sum(max(0,amt(r.get('amount',0))-amt(r.get('paid',0))) for r in receivables),2), open_supplier_balance=round(sum(max(0,amt(b.get('amount',0))-amt(b.get('paid',0))) for b in bills),2), issues=len(issues)), issues=issues, checked_at=stamp(), note='Read-only audit. Missing links are not automatically created. Historical manual records may require review.')


# Revision 34: conservative, explicit reconciliation of invoice -> receivable.
# Supplier bills are never inferred from POs: receipt != supplier invoice.
@router.get('/reconciliation/plan')
def reconciliation_plan(request: Request):
    """Dry run. Report eligible links and anomalies without changing stored records."""
    guard(request)
    with lock:
        return _invoice_link_plan(request)

def _invoice_link_plan(request):
    docs = ws.load(ws.location(request, 'doorks', 'estimates_invoices'))
    receivables = ac.read(ac.base(request) / 'receivables.json')
    by_id = {}
    for doc in docs:
        by_id.setdefault(str(doc.get('id') or ''), []).append(doc)
    linked = {}
    for ar in receivables:
        source = str(ar.get('source_invoice_id') or '')
        if source: linked.setdefault(source, []).append(ar)
    eligible, skipped = [], []
    for doc in docs:
        if str(doc.get('document_type') or '').lower() != 'invoice':
            continue
        id = str(doc.get('id') or '')
        number = str(doc.get('document_number') or '')
        reason = None
        if not id or len(by_id[id]) != 1: reason = 'missing_or_duplicate_invoice_id'
        elif linked.get(id): reason = 'already_linked'
        else:
            try:
                total = amt(doc.get('total') if doc.get('total') is not None else doc.get('amount', 0))
                paid = amt(doc.get('paid') or 0)
                if total <= 0: reason = 'zero_total_requires_review'
                elif paid > total: reason = 'paid_exceeds_total'
            except HTTPException:
                reason = 'invalid_amount'
        if reason:
            skipped.append(dict(invoice_id=id, number=number, reason=reason))
        else:
            eligible.append(dict(invoice_id=id, number=number, amount=total, paid=paid))
    return dict(eligible=eligible, skipped=skipped, eligible_count=len(eligible), skipped_count=len(skipped), note='Only missing invoice receivables are eligible. No supplier bills or payments are created automatically.')

@router.post('/reconciliation/apply-invoice-links')
def apply_invoice_links(request: Request):
    """Explicitly create missing invoice balances; safe to repeat without duplicates."""
    guard(request)
    with lock:
        plan = _invoice_link_plan(request)
        path = ac.base(request) / 'receivables.json'
        rows = ac.read(path)
        docs = ws.load(ws.location(request, 'doorks', 'estimates_invoices'))
        invoices = {str(d.get('id')): d for d in docs if str(d.get('document_type') or '').lower() == 'invoice'}
        created = []
        for candidate in plan['eligible']:
            id = candidate['invoice_id']
            if any(str(r.get('source_invoice_id') or '') == id for r in rows):
                continue
            invoice = invoices[id]
            total, paid = candidate['amount'], candidate['paid']
            record = dict(id=uuid.uuid4().hex, source_invoice_id=id,
                invoice_number=str(invoice.get('document_number') or ''),
                customer=str(invoice.get('customer') or invoice.get('customer_name') or ''),
                job_number=str(invoice.get('work_order_number') or invoice.get('job_number') or ''),
                amount=total, paid=paid,
                status='Paid' if paid >= total else ('Partially Paid' if paid else 'Open'),
                created_at=stamp())
            rows.append(record)
            created.append(record)
        if created:
            ac.write(path, rows)
            # Events are supplementary; the receivable file is the authoritative result.
            for record in created:
                event(request, 'invoice', record['source_invoice_id'], 'receivable_created', record['amount'], 'Rev34 reconciliation')
        return dict(created_count=len(created), created=created, skipped=plan['skipped'], already_reconciled=(len(created)==0))


# Revision 38: consolidated, read-only Doorks financial snapshot.
# Workflow records and manually entered ledger records are distinct sources;
# do not add their totals together as if they were reconciled bank transactions.
@router.get('/financial-snapshot')
def financial_snapshot(request: Request):
    guard(request)
    from app.routers import accounting_ledger as ledger
    from decimal import Decimal
    def number(value):
        try:
            n = Decimal(str(value if value is not None and value != '' else 0))
            if not n.is_finite() or n < 0: raise ValueError()
            return n
        except (ValueError, TypeError, InvalidOperation):
            raise HTTPException(422, 'Invalid amount in stored Doorks financial record')
    def cents(n): return float(n.quantize(Decimal('0.01')))
    with lock:
        folder = ac.base(request)
        receivables = ac.read(folder/'receivables.json')
        supplier_bills = ac.read(folder/'supplier_bills.json')
        receipts = ac.read(folder/'receipts.json')
        manual_bills = ledger.load(ledger.path(request,'doorks','bills'))
        manual_payments = ledger.load(ledger.path(request,'doorks','payments'))
        workflow_events = ws.load(folder/'workflow_events.json')
    warnings=[]
    def aggregate(rows, kind):
        gross=paid=Decimal('0')
        for item in rows:
            if str(item.get('status','')).lower() in ('void','voided','cancelled','canceled'):continue
            total=number(item.get('amount',0)); applied=number(item.get('paid',0))
            if applied>total:
                warnings.append(dict(kind=kind,id=str(item.get('id','')),message='Recorded payments exceed original amount'))
            gross+=total;paid+=applied
        return dict(count=len(rows),total=cents(gross),paid=cents(paid),outstanding=cents(max(Decimal('0'),gross-paid)))
    ar=aggregate(receivables,'customer_receivable')
    ap=aggregate(supplier_bills,'workflow_supplier_bill')
    manual_bill_total=sum((number(x.get('amount',0)) for x in manual_bills if str(x.get('status','')).lower()!='voided'),Decimal('0'))
    manual_received=sum((number(x.get('amount',0)) for x in manual_payments if x.get('direction')=='received'),Decimal('0'))
    manual_sent=sum((number(x.get('amount',0)) for x in manual_payments if x.get('direction')=='sent'),Decimal('0'))
    approved_receipts=sum((number(x.get('amount',0)) for x in receipts if x.get('authorization_status')=='Authorized'),Decimal('0'))
    pending_receipts=sum(1 for x in receipts if x.get('authorization_status')!='Authorized')
    for bill in manual_bills:
        if any(str(bill.get('bill_number','')).strip().casefold()==str(w.get('bill_number','')).strip().casefold() and str(bill.get('supplier','')).strip().casefold()==str(w.get('vendor','')).strip().casefold() and bill.get('bill_number') for w in supplier_bills):
            warnings.append(dict(kind='possible_duplicate_supplier_bill',id=str(bill.get('id','')),message='Same supplier and bill number appear in manual ledger and Connected Workflows'))
    return dict(customer_receivables=ar,workflow_supplier_bills=ap,
        manual_ledger=dict(bills_count=len(manual_bills),bills_total=cents(manual_bill_total),payments_count=len(manual_payments),customer_payments=cents(manual_received),supplier_payments=cents(manual_sent)),
        receipts=dict(count=len(receipts),authorized_total=cents(approved_receipts),pending_count=pending_receipts),
        workflow_events_count=len(workflow_events),warnings=warnings,generated_at=stamp(),
        note='Separate source totals, NOT additive. Manual payments are unverified and may duplicate workflow payments. This is not a bank reconciliation or accrual financial statement.')


# Rev 39: read-only operational preflight. No writes, no external payment or payroll actions.
def _preflight_findings(docs, orders, ar, bills, payroll, stock):
    from collections import Counter
    findings=[]
    def add(area, code, severity, detail, reference=''):
        findings.append(dict(area=area,code=code,severity=severity,detail=detail,reference=str(reference)[:120]))
    invoices=[d for d in docs if str(d.get('document_type','')).lower()=='invoice']
    invoice_ids={str(d.get('id')) for d in invoices if d.get('id')}
    linked=Counter(str(r.get('source_invoice_id')) for r in ar if r.get('source_invoice_id'))
    for d in invoices:
        key=str(d.get('id') or '')
        if not key or linked[key]==0:add('invoicing','missing_receivable','warning','Invoice has no linked receivable',d.get('document_number',''))
        if linked[key]>1:add('invoicing','duplicate_receivable','blocker','Invoice has multiple linked receivables',d.get('document_number',''))
    for r in ar:
        if r.get('source_invoice_id') and str(r['source_invoice_id']) not in invoice_ids:
            add('invoicing','orphan_receivable','blocker','Receivable references a missing invoice',r.get('invoice_number',''))
        try:
            if amt(r.get('paid',0))>amt(r.get('amount',0)):add('invoicing','overpaid_receivable','blocker','Customer payments exceed receivable amount',r.get('invoice_number',''))
        except HTTPException:add('invoicing','invalid_receivable_amount','blocker','Receivable contains invalid financial amounts',r.get('invoice_number',''))
    po_ids={str(p.get('id')) for p in orders if p.get('id')}
    bill_keys=Counter((str(b.get('source_po_id') or ''),str(b.get('bill_number') or '').strip().casefold()) for b in bills)
    for b in bills:
        if b.get('source_po_id') and str(b['source_po_id']) not in po_ids:
            add('purchasing','orphan_supplier_bill','blocker','Supplier bill references missing PO',b.get('bill_number',''))
        key=(str(b.get('source_po_id') or ''),str(b.get('bill_number') or '').strip().casefold())
        if key[1] and bill_keys[key]>1:add('purchasing','duplicate_supplier_bill','blocker','Duplicate supplier bill number for PO',b.get('bill_number',''))
        try:
            if amt(b.get('paid',0))>amt(b.get('amount',0)):add('purchasing','overpaid_supplier_bill','blocker','Supplier payments exceed bill',b.get('bill_number',''))
        except HTTPException:add('purchasing','invalid_supplier_amount','blocker','Supplier bill has invalid amount',b.get('bill_number',''))
    for p in orders:
        try:
            if amt(p.get('received_quantity',0))>amt(p.get('quantity',0)):
                add('purchasing','over_received','blocker','Received quantity exceeds PO quantity',p.get('po_number',''))
        except HTTPException:add('purchasing','invalid_po_quantity','blocker','PO contains invalid quantity',p.get('po_number',''))
    for card in payroll:
        if str(card.get('approval_status','')).lower() not in ('approved','') and card.get('approval_status'):
            add('payroll','unapproved_timecard','warning','Timecard not approved',card.get('id',''))
    for item in stock.get('items',[]):
        if float(item.get('on_hand') or 0)<-0.000001:
            add('inventory','negative_stock','blocker','Calculated on-hand quantity is negative',item.get('sku',''))
    return findings

@router.get('/phase1-preflight')
def phase1_preflight(request: Request):
    """Doorks-only, read-only diagnostics; not a claim of full integration test coverage."""
    guard(request)
    from app.routers import doorks_operations as operations
    with lock:
        docs=ws.load(ws.location(request,'doorks','estimates_invoices'))
        orders=ws.load(ws.location(request,'doorks','purchase_orders'))
        ar=ac.read(ac.base(request)/'receivables.json')
        bills=ac.read(ac.base(request)/'supplier_bills.json')
        payroll=ws.load(ws.location(request,'doorks','payroll'))
        stock=operations.stock_snapshot(request)
    findings=_preflight_findings(docs,orders,ar,bills,payroll,stock)
    return dict(status='review_required' if findings else 'no_issues_detected',
        checked_at=stamp(),counts=dict(invoices=sum(str(d.get('document_type','')).lower()=='invoice' for d in docs),
        purchase_orders=len(orders),receivables=len(ar),supplier_bills=len(bills),timecards=len(payroll),stock_parts=len(stock.get('items',[]))),
        blockers=sum(f['severity']=='blocker' for f in findings),warnings=sum(f['severity']=='warning' for f in findings),
        findings=findings,note='Read-only checks of stored Doorks records only. A clean result does not prove workflows, payroll compliance, financial statement accuracy, permissions, or Render deployment have passed live tests.')
