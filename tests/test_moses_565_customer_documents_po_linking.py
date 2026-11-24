"""Moses 5.65 ticket, document and PO follow-through (isolated temporary data)."""
from pathlib import Path
from types import SimpleNamespace
import json
import os
import pytest
from fastapi import HTTPException
from app.routers import pds_purchase_orders as po
from app.services import moses_pds_document_email as mail

ROOT = Path(__file__).resolve().parents[1]

class Jobs:
    def __init__(self):
        self.jobs = [{'id':'job-fixed-5','job_number':'100344','customer':'Saddleback Design Co.',
                      'status':'Quote','po_number':'','date':'2026-11-29'}]
        self.writes = []
    def list_jobs(self):
        return [dict(j) for j in self.jobs]
    def update_job(self, job_id, changes):
        record = next(j for j in self.jobs if j['id']==job_id)
        record.update(changes);self.writes.append((job_id, dict(changes)))
        return dict(record)

def req(folder, jobs, role='office_admin'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'owner-1','name':'Office Admin'},auth_role=role),
      session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(data_dir=folder,calendar_store=jobs)))

def payload(**updates):
    data={'vendor':'Test Supplier','work_order':'100344','work_order_number':'100344',
          'job_id':'job-fixed-5','customer':'Saddleback Design Co.','status':'Draft',
          'quantity':'2','total':'100','line_items':json.dumps([{'item':'TEST','description':'Door part','quantity':2,'rate':50}]),
          'date':'2026-11-24','tracking_number':'','arrival_date':''}
    data.update(updates)
    return po.POInput(data=data)

def test_saved_supplier_po_links_to_job_without_overwriting_customer_po(tmp_path):
    jobs=Jobs();r=req(tmp_path,jobs)
    one=po.create_order(payload(tracking_number='UPS999',arrival_date='2026-11-30'),r)
    assert one['job_id']=='job-fixed-5' and one['work_order']=='100344'
    assert one['work_order_number']=='100344' and one['customer']=='Saddleback Design Co.'
    assert one['tracking_number']=='UPS999' and one['arrival_date']=='2026-11-30'
    assert jobs.jobs[0]['po_number']==''  # Customer PO stays independent
    two=po.create_order(payload(tracking_number='DHL888'),r)
    assert two['job_id']==one['job_id'] and two['po_number']!=one['po_number']
    assert jobs.jobs[0]['po_number']==''  # Customer PO stays independent
    listed=po.list_orders(r)['items']; assert len(listed)==2
    assert all(x['job_id']=='job-fixed-5' for x in listed)
    assert not jobs.writes

def test_unmatched_or_other_customer_po_does_not_allocate_number(tmp_path):
    jobs=Jobs();r=req(tmp_path,jobs)
    for changes in (
        {'work_order':'00-0000','work_order_number':'00-0000','job_id':''},
        {'customer':'Another company'},
        {'job_id':'not-the-linked-job'},
        {'status':'Received'},
        {'arrival_date':'2030-31-99'},
    ):
        with pytest.raises(HTTPException): po.create_order(payload(**changes),r)
    assert not (tmp_path/'pds_purchase_orders'/'sequence.json').exists()
    assert not jobs.writes

def test_po_tracking_and_receiving_are_distinct(tmp_path):
    jobs=Jobs();r=req(tmp_path,jobs)
    one=po.create_order(payload(),r)
    edits=payload(status='En Route',tracking_number='123456',arrival_date='2026-12-02')
    updated=po.update_order(one['id'],edits,r)
    assert updated['status']=='En Route' and updated['tracking_number']=='123456'
    with pytest.raises(HTTPException):
        po.update_order(one['id'],payload(status='Received'),r)
    event=po.receive_po('pds',one['id'],po.ReceiveInput(quantity=2,request_id='receipt-unique-1',reference='Vendor slip #89'),r)
    assert event['outstanding']==0
    saved=po.list_orders(r)['items'][0]
    assert saved['status']=='Received' and saved['received_status']=='Received'
    assert po.receive_po('pds',one['id'],po.ReceiveInput(quantity=2,request_id='receipt-unique-1'),r)['duplicate']

def test_po_stock_order_remains_unassigned(tmp_path):
    jobs=Jobs();r=req(tmp_path,jobs)
    saved=po.create_order(payload(work_order='',work_order_number='',job_id='',customer='PDS Stock'),r)
    assert saved['work_order']=='' and saved['job_id']==''
    assert not jobs.writes

def test_ticket_original_alternate_and_existing_ai_paths_are_reused():
    js=(ROOT/'static/app.js').read_text()
    assert "alternateUpload.textContent='Alternate'" in js
    assert "['Estimate','estimate']" in js and "['Invoice','invoice']" in js
    assert "['Purchase Order','purchase_order']" in js
    assert "['Receipt','Receipt']" in js and "['Packing Slip','Packing Slip']" in js
    assert 'attachExisting.textContent' not in js
    assert "renderDocumentVault('pds',type" in js
    assert "fetch('/receipts/extract'" in js
    assert "badge.className='badge';navAccounting.append(badge)" in js

def test_saved_docs_have_real_delivery_status_and_correct_edit_path():
    js=(ROOT/'static/app.js').read_text()
    assert "marker.textContent='Saved PDF'" in js
    assert "marker.textContent='Resend Accepted'" in js
    assert "marker.textContent='Delivered to mail server'" in js
    assert "editSaved.textContent='View/Edit'" in js
    assert "edit.textContent='View/Edit Linked Document'" in js
    assert "preview.send_enabled===false" in js
    assert 'Approve & Send via Resend' in js
    assert 'MOSES_PDS_DOCUMENT_SEND_ENABLED' in (ROOT/'app/services/moses_pds_document_email.py').read_text()

def test_po_status_and_sender_remain_authorized():
    js=(ROOT/'static/app.js').read_text()
    assert "['tracking_number','Tracking Number']" in js
    assert "['arrival_date','Expected Arrival']" in js
    assert "['Draft','Ordered','Shipped','En Route','Delivered','Received','Cancelled']" in js
    assert "data.job_id=data.work_order_number?form.dataset.linkedJobId||'':''" in js
    assert "po.job_id||''" in js
    assert 'MOSES_PO_SEND_ENABLED' in (ROOT/'app/services/moses_po_delivery.py').read_text()

def test_pds_document_preview_exposes_send_switch(monkeypatch):
    monkeypatch.delenv('MOSES_PDS_DOCUMENT_SEND_ENABLED',raising=False)
    monkeypatch.setattr(mail,'_snapshot',lambda *_:{'number':'RE00097','kind':'estimate','pdf_sha256':'xyz'})
    request=object()
    assert mail.preview(request,'estimate','RE00097')['send_enabled'] is False
    monkeypatch.setenv('MOSES_PDS_DOCUMENT_SEND_ENABLED','true')
    assert mail.preview(request,'estimate','RE00097')['send_enabled'] is True
