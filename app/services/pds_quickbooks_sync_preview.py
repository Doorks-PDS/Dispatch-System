"""Office-only, adapter-neutral previews of 5.71 prepared invoice/PO handoffs.

The returned data describes what a later QBO/Desktop adapter must match. It
cannot be directly sent to QuickBooks: customer/vendor IDs, item accounts, tax
rules and company authorization are intentionally unfilled.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb
from app.services import pds_quickbooks_purchase_orders as po
from app.services import pds_quickbooks_numbering as numbers

CENT = Decimal('0.01')


def _prepared(request, kind, number, current):
    ledger_path = qb._ledger_path(request) if kind == 'invoice' else po._path(request)
    item = qb._load(ledger_path)['items'].get(number)
    if not isinstance(item, dict) or item.get('state') != 'prepared_for_review':
        raise HTTPException(409, 'Prepare this reviewed PDS record before sync preview')
    if item.get('fingerprint') != current.get('fingerprint'):
        raise HTTPException(409, 'Source record changed after preparation; reconcile first')
    if not current.get('ready'):
        raise HTTPException(409, 'Source record requires office review')
    refs = numbers._references(request)
    key = ('invoice' if kind == 'invoice' else 'supplier_po')+':'+number
    if key in refs:
        raise HTTPException(409, 'Already linked to a QuickBooks transaction; reconcile with the provider')
    return item


def _money_str(raw):
    return str(qb._money(raw).quantize(CENT, rounding=ROUND_HALF_UP))


def preview_invoice(request, number):
    qb._admin(request)
    number = str(number or '').upper()
    if not qb.INVOICE_RE.fullmatch(number):
        raise HTTPException(422, 'Exact PDS invoice number required')
    current = qb._rows(request).get(number)
    if not current:
        raise HTTPException(404, 'PDS invoice not found')
    _prepared(request, 'invoice', number, current)
    matches = [item for item in request.app.state.documents_store.list_documents()
               if isinstance(item, dict) and item.get('type') == 'invoice'
               and str(item.get('number') or '').upper() == number]
    if len(matches) != 1:
        raise HTTPException(409, 'Invoice metadata is not unique')
    source = matches[0]
    lines = []
    for pos, line in enumerate(source.get('items') or [], start=1):
        if not isinstance(line, dict):
            raise HTTPException(409, 'Invoice source line invalid')
        quantity, rate = qb._money(line.get('qty')), qb._money(line.get('rate'))
        if quantity <= 0 or rate < 0:
            raise HTTPException(409, 'Invalid invoice line amount')
        lines.append({'position':pos, 'description':str(line.get('description') or line.get('name') or '')[:2000],
                      'quantity':str(quantity), 'unit_price':_money_str(rate),
                      'amount':_money_str(quantity*rate),
                      'taxable_in_pds':bool(line.get('taxable', True)),
                      'qb_item_reference':None, 'qb_tax_code_reference':None})
    policies,_ = numbers._policies(request)
    return {'kind':'invoice', 'pds_number':number, 'job_number':current['job_number'],
            'pds_customer':current['customer'], 'date':current['date'],
            'terms':current['terms'], 'subtotal':current['subtotal'], 'tax':current['tax'],
            'total':current['total'], 'lines':lines, 'currency':'USD',
            'source_fingerprint':current['fingerprint'],
            'idempotency_reference':'PDS:invoice:'+number,
            'number_policy':policies['invoice'],
            'mapping_pending':['QuickBooks company','customer','income items','tax codes','terms'],
            'can_post':False, 'sync_state':'prepared_not_synced',
            'external_payment_link':None, 'payment_posted':False}


def preview_supplier_po(request, number):
    qb._admin(request)
    number = str(number or '').upper()
    if not po.PO_RE.fullmatch(number):
        raise HTTPException(422, 'Exact supplier PO number required')
    current = po._rows(request).get(number)
    if not current:
        raise HTTPException(404, 'PDS supplier PO not found')
    _prepared(request, 'supplier_po', number, current)
    matches=[item for item in po._source(request)
             if str(item.get('po_number') or '').upper()==number]
    if len(matches) != 1:
        raise HTTPException(409, 'Supplier PO source is not unique')
    source=matches[0]
    lines=source.get('line_items') or []
    if isinstance(lines,str):
        try:lines=json.loads(lines)
        except ValueError as exc:raise HTTPException(409,'Supplier PO line items invalid') from exc
    if not isinstance(lines,list):
        raise HTTPException(409,'Supplier PO line items invalid')
    normalized=[]
    for pos,line in enumerate(lines,start=1):
        if not isinstance(line,dict):
            raise HTTPException(409, 'Supplier PO source line invalid')
        qty,rate=qb._money(line.get('quantity')),qb._money(line.get('rate'))
        normalized.append({'position':pos,'description':str(line.get('description') or line.get('item') or '')[:2000],
                           'quantity':str(qty), 'unit_cost':_money_str(rate),
                           'amount':_money_str(qty*rate), 'qb_purchase_item_reference':None})
    policies,_=numbers._policies(request)
    return {'kind':'supplier_po', 'pds_number':number, 'pds_source_id':current['source_id'],
            'pds_supplier':current['vendor'], 'job_number':current['job_number'],
            'date':current['date'], 'status':current['order_status'],
            'subtotal':current['subtotal'], 'tax':current['tax'],
            'shipping':current['shipping'], 'total':current['total'],
            'lines':normalized,'currency':'USD', 'source_fingerprint':current['fingerprint'],
            'idempotency_reference':'PDS:supplier_po:'+number,
            'number_policy':policies['supplier_po'],
            'mapping_pending':['QuickBooks company','vendor','expense/items','tax/shipping'],
            'can_post':False, 'sync_state':'prepared_not_synced',
            'supplier_bill_created':False, 'payment_posted':False}
