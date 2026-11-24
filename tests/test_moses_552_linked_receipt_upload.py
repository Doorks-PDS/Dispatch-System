"""5.52: receipts and packing slips created from tickets use existing PDS source."""
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import asyncio
import json
from fastapi import UploadFile
from app.routers import receipts

ROOT = Path(__file__).resolve().parents[1]


def request(tmp_path, role='tech'):
    state=SimpleNamespace(data_dir=str(tmp_path),auth_role=role,
        auth_user={'id':'employee1','name':'Test Technician'})
    return SimpleNamespace(state=state,app=SimpleNamespace(state=state))


def upload(tmp_path,kind,amount):
    req=request(tmp_path)
    file=UploadFile(filename='original.pdf', file=BytesIO(b'%PDF-1.4 receipt original'))
    return asyncio.run(receipts.create_receipt(
        req,date='2026-11-24',employee='Test Technician',vendor='Door Supply',
        amount=amount,document_type=kind,job_number='1126-15',customer='North Italia',
        po_number='QB-1188',file=file,card_last4='',notes='',category='Other',stock_reference='',receipt_number='',x_api_key=None))['item']


def test_job_receipt_and_packing_slip_reuse_one_store(tmp_path):
    receipt=upload(tmp_path,'Receipt',124.56)
    packing=upload(tmp_path,'Packing Slip',0.0)
    assert {receipt['document_type'],packing['document_type']} == {'Receipt','Packing Slip'}
    assert receipt['job_number']==packing['job_number']=='1126-15'
    assert receipt['po_number']==packing['po_number']=='QB-1188'
    assert receipt['uploaded_by_id']==packing['uploaded_by_id']=='employee1'
    assert receipt['authorization_status']=='Pending Authorization'
    saved=json.loads((tmp_path/'receipts'/'receipts.json').read_text())
    assert len(saved)==2
    assert all((tmp_path/'receipts'/row['stored_file']).exists() for row in saved)
    # Posting an attachment never changes warehouse inventory or a PO ledger.
    assert not (tmp_path/'document_vault').exists()
    assert not (tmp_path/'pds_purchase_orders').exists()


def test_ticket_uses_existing_receipts_route_and_same_receiving_register():
    js=(ROOT/'static/app.js').read_text()
    assert 'function openJobReceiptUpload(job, documentType, ticketContainer, ctx)' in js
    assert "['Receipt','Receipt']" in js and "['Packing Slip','Packing Slip']" in js
    assert "fd.set('job_number',String(job.job_number||''))" in js
    assert "fd.set('document_type',type)" in js
    assert "fetch('/receipts',{method:'POST',credentials:'same-origin',body:fd})" in js
    assert "window.__pdsReceiptViewType='Packing Slip'" in js
    assert "window.__pdsReceiptViewType='Receipt'" in js
    assert "selectedType.value=window.__pdsReceiptViewType||'all'" in js
    assert 'name="document_type"><option value="Receipt">Receipt</option><option value="Packing Slip">Packing Slip</option>' in js
    assert 'renderJobDetails(ticketContainer,job,ctx)' in js
    receipt_view=(ROOT/'static/pds_accounting_tickets.js').read_text()
    assert "const data=await request('/receipts')" in receipt_view
    assert "String(r.job_number||'').trim().toLowerCase()" in receipt_view
