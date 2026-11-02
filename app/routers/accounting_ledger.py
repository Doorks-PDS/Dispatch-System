"""Workspace-isolated manual AP/AR ledger. No external payment processing.
All payment records are manual/unverified; no bank settlement claims.
"""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix='/accounting-ledger', tags=['accounting-ledger'])
LOCK = RLock()
PLATFORMS = {'pds', 'doorks', 'sdc'}
KINDS = {'bills', 'payments'}
class Payload(BaseModel):
    data: dict

def guard(request: Request, platform: str):
    if platform not in PLATFORMS: raise HTTPException(404, 'Unknown workspace')
    if not getattr(request.state, 'auth_user', None): raise HTTPException(401, 'Login required')
    if getattr(request.state, 'auth_role', None) != 'office_admin': raise HTTPException(403, 'Office Admin required')
    if request.session.get('active_platform', 'pds') != platform: raise HTTPException(403, 'Switch workspace first')
    # PDS also requires its existing accounting unlock before any ledger access.
    if platform == 'pds':
        # Do not expose new PDS ledger routes without integrating the original PIN state.
        raise HTTPException(403, 'PDS ledger awaiting existing accounting PIN integration')

def path(request, platform, kind):
    base = Path(request.app.state.data_dir) / 'accounting_ledger' / platform
    base.mkdir(parents=True, exist_ok=True)
    return base / (kind + '.json')

def load(p):
    if not p.exists(): return []
    data=json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(data,list): raise HTTPException(500,'Invalid ledger store')
    return data

def write(p, data):
    tmp=p.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)

def money(value, field):
    try: n=Decimal(str(value))
    except (InvalidOperation,ValueError): raise HTTPException(422,f'Invalid {field}')
    if not n.is_finite() or n<0 or n.as_tuple().exponent < -2: raise HTTPException(422,f'Invalid {field}')
    return n

def normalize(kind,data):
    data=dict(data)
    if kind=='bills':
        if not str(data.get('supplier','')).strip(): raise HTTPException(422,'Supplier required')
        if not str(data.get('bill_number','')).strip(): raise HTTPException(422,'Bill number required')
        data['amount']=str(money(data.get('amount',0),'bill amount'))
        data['status']=str(data.get('status') or 'Open')
        if data['status'] not in ('Open','On Hold','Voided'):raise HTTPException(422,'Invalid bill status')
    else:
        if data.get('direction') not in ('received','sent'):raise HTTPException(422,'Invalid payment direction')
        if data.get('method') not in ('Check','Cash','ACH','E-Check','Card','Wire','Other'):raise HTTPException(422,'Invalid payment method')
        if not str(data.get('reference_id','')).strip():raise HTTPException(422,'Invoice or bill reference required')
        data['amount']=str(money(data.get('amount',0),'payment amount'))
        if money(data['amount'],'payment amount')==0:raise HTTPException(422,'Payment must be greater than zero')
        data['verification']='Manual entry — unverified'
    return data

@router.get('/{platform}/summary')
def summary(platform:str,request:Request):
    guard(request,platform)
    with LOCK:
        bills=load(path(request,platform,'bills'));payments=load(path(request,platform,'payments'))
    totals={'bills':len(bills),'payments':len(payments),'billed':0.0,'paid_to_suppliers':0.0,'received_from_customers':0.0}
    totals['billed']=round(sum(float(x['amount']) for x in bills if x.get('status')!='Voided'),2)
    for item in payments:
        key='paid_to_suppliers' if item['direction']=='sent' else 'received_from_customers'
        totals[key]=round(totals[key]+float(item['amount']),2)
    return totals


@router.get('/{platform}/{kind}')
def listing(platform:str,kind:str,request:Request):
    guard(request,platform)
    if kind not in KINDS:raise HTTPException(404,'Unknown collection')
    with LOCK:return {'items':load(path(request,platform,kind))}

@router.post('/{platform}/{kind}')
def create(platform:str,kind:str,request:Request,payload:Payload):
    guard(request,platform)
    if kind not in KINDS:raise HTTPException(404,'Unknown collection')
    record=normalize(kind,payload.data)
    with LOCK:
        p=path(request,platform,kind);items=load(p)
        if kind=='bills' and any(x.get('bill_number','').casefold()==str(record['bill_number']).casefold() and x.get('supplier','').casefold()==str(record['supplier']).casefold() for x in items):raise HTTPException(409,'Duplicate supplier bill number')
        record.update(id=uuid.uuid4().hex,created_at=datetime.now(timezone.utc).isoformat(),created_by=str(request.state.auth_user))
        items.append(record);write(p,items)
    return {'item':record}

@router.patch('/{platform}/bills/{record_id}')
def update_bill(platform:str,record_id:str,request:Request,payload:Payload):
    guard(request,platform)
    with LOCK:
        p=path(request,platform,'bills');items=load(p)
        for index,item in enumerate(items):
            if item['id']==record_id:
                merged={**item,**payload.data};normalized=normalize('bills',merged)
                normalized['id']=item['id'];normalized['created_at']=item['created_at'];normalized['created_by']=item['created_by']
                normalized['updated_at']=datetime.now(timezone.utc).isoformat();items[index]=normalized;write(p,items)
                return {'item':normalized}
    raise HTTPException(404,'Bill not found')

