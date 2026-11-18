"""PDS invoice handoff packets: verified office review only, never official invoices.

Packages are read-only snapshots of existing jobs. They do not create invoice
numbers, prices, payments, customer contacts, or accounting entries.
"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException


def _guard(request):
    if (not getattr(request.state,'auth_user',None) or
        request.session.get('active_platform')!='pds' or
        getattr(request.state,'auth_role',None) not in ('office_admin','office','lead')):
        raise HTTPException(403,'PDS office access required')


def _connect(request):
    folder=Path(request.app.state.data_dir)/'moses_pds'
    folder.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(str(folder/'invoice_handoffs.sqlite3'), timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS handoffs (
        id TEXT PRIMARY KEY,job_id TEXT NOT NULL,job_hash TEXT NOT NULL,
        source_json TEXT NOT NULL,created_at TEXT NOT NULL,
        UNIQUE(job_id,job_hash))''')
    db.commit()
    return db


def _source(request,job_id):
    if not isinstance(job_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,80}',job_id):
        raise HTTPException(422,'Exact PDS internal job ID required')
    store=getattr(request.app.state,'calendar_store',None)
    if not store:raise HTTPException(503,'PDS job store unavailable')
    job=store.get_job(job_id)
    if not isinstance(job,dict) or str(job.get('id')) != job_id:
        raise HTTPException(404,'Verified PDS job not found')
    return job


def _snapshot(job):
    keys=('id','job_number','customer','status','date','address',
          'invoice_number','estimate_number','sent_quote_number')
    return {k:str(job.get(k) or '')[:250] for k in keys}


def _hash(job):
    return hashlib.sha256(json.dumps(job,sort_keys=True,default=str).encode()).hexdigest()


def inspect(request,job_id):
    _guard(request)
    job=_source(request,job_id)
    snap=_snapshot(job)
    docs=request.app.state.documents_store.list_documents(job_id=job_id)
    if not isinstance(docs,list):
        raise HTTPException(503,'PDS document index unavailable')
    linked=[d for d in docs if isinstance(d,dict) and str(d.get('job_id') or '')==job_id]
    existing=[d for d in linked if str(d.get('type') or '').lower()=='invoice']
    has_invoice=bool(snap['invoice_number']) or bool(existing)
    eligible=snap['status'].strip().casefold() in ('to be invoiced','complete','completed') and not has_invoice
    return {'workspace':'pds','job':snap,'source_hash':_hash(job),
            'existing_invoices':[str(d.get('number') or '')[:50] for d in existing],
            'ready_for_manual_review':eligible, 'official_invoice_created':False,
            'reason':('Invoice already exists or is referenced' if has_invoice else
                      'Not in a completed/billing-ready status' if not eligible else
                      'Review technician work, existing documents, pricing, and customer before invoicing'),
            'note':'Source-backed review only; no official invoice number is allocated.'}


def prepare(request,limit=25):
    _guard(request)
    if getattr(request.state,'auth_role',None)!='office_admin':
        raise HTTPException(403,'PDS office-admin required to save handoff reviews')
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=50:
        raise HTTPException(422,'Limit must be between 1 and 50')
    jobs=request.app.state.calendar_store.list_jobs()
    if not isinstance(jobs,list):
        raise HTTPException(503,'PDS jobs unavailable')
    # Only explicitly flagged billing-ready work; do not bulk-infer from completed jobs.
    candidates=[j for j in jobs if isinstance(j,dict) and
                str(j.get('status') or '').strip().casefold()=='to be invoiced']
    candidates.sort(key=lambda x:(str(x.get('date') or ''),str(x.get('id') or '')))
    saved=[]
    with _connect(request) as db:
        for job in candidates:
            job_id=str(job.get('id') or '')
            if not re.fullmatch('[A-Za-z0-9_-]{1,80}',job_id):continue
            review=inspect(request,job_id)
            if not review['ready_for_manual_review']:continue
            key=review['source_hash']
            existing=db.execute('SELECT id FROM handoffs WHERE job_id=? AND job_hash=?',(job_id,key)).fetchone()
            if existing:
                saved.append({'id':existing['id'],'job_id':job_id,'existing':True})
            else:
                hid=uuid.uuid4().hex
                db.execute('INSERT INTO handoffs VALUES (?,?,?,?,?)',
                           (hid,job_id,key,json.dumps(review['job']),datetime.now(timezone.utc).isoformat()))
                saved.append({'id':hid,'job_id':job_id,'existing':False})
            if len(saved)>=limit:break
    return {'workspace':'pds','saved_review_packets':saved,'count':len(saved),
            'official_invoices_created':0,'approval_required_before_invoice':True}


def receipts(request):
    _guard(request)
    with _connect(request) as db:
        rows=db.execute('SELECT id,job_id,job_hash,source_json,created_at FROM handoffs ORDER BY created_at DESC LIMIT 60').fetchall()
    result=[]
    for row in rows:
        data=json.loads(row['source_json'])
        result.append({'id':row['id'],'job_id':row['job_id'],'job_number':data.get('job_number'),
                       'created_at':row['created_at'],'kind':'invoice_review_packet',
                       'status':'saved_for_review','official_invoice_created':False})
    return {'workspace':'pds','read_only':True,'receipts':result}
