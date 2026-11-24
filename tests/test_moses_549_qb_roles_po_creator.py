"""PDS 5.49: creator identity, role boundaries and external QB document traceability.

No live customer, provider or production disk access.
"""
from types import SimpleNamespace
from pathlib import Path
import asyncio
import json
import pytest
from fastapi import HTTPException

from app.routers import pds_purchase_orders as po
from app.routers import document_vault as vault
from app.routers import documents

ROOT=Path(__file__).resolve().parents[1]


def request(path, role='office_admin', name='PDS Employee', uid='emp-1'):
    return SimpleNamespace(
        state=SimpleNamespace(auth_user={'id':uid,'name':name,'username':'user'},auth_role=role),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=path,
            require_key=lambda x, request=None: role)),
    )


def test_purchase_order_creator_is_authenticated_and_immutable(tmp_path):
    req=request(tmp_path,role='lead',name='Steven Carpenter',uid='lead-7')
    demo_job={'id':'pds-job-15','job_number':'1126-15','customer':'Test Account','po_number':''}
    req.app.state.calendar_store=SimpleNamespace(list_jobs=lambda:[demo_job],update_job=lambda _id,changes:{**demo_job,**changes})
    created=po.create_order(po.POInput(data={'vendor':'Parts Supplier','work_order':'1126-15',
                 'status':'Draft','created_by':'Spoofed Name'}),req)
    assert created['created_by']=='Steven Carpenter'
    assert created['created_by_id']=='lead-7'
    assert created['created_by_role']=='lead'
    assert created['created_at']
    first_time=created['created_at']
    other=request(tmp_path,role='office',name='Office Clerk',uid='office-2')
    other.app.state.calendar_store=req.app.state.calendar_store
    updated=po.update_order(created['id'],po.POInput(data={
        'vendor':'Parts Supplier','notes':'Delivery expected tomorrow',
        'created_by':'Attempt to change creator','created_by_id':'spoof'}),other)
    assert updated['created_by']=='Steven Carpenter'
    assert updated['created_by_id']=='lead-7'
    assert updated['created_at']==first_time
    assert updated['updated_by']=='Office Clerk'
    assert json.loads((tmp_path/'pds_purchase_orders'/'records.json').read_text())[0]['created_by']=='Steven Carpenter'


def test_purchase_order_requires_employee_identity_and_limits_lead_writes(tmp_path):
    bad=request(tmp_path,role='lead')
    bad.state.auth_user={'name':'Unknown Employee'}
    with pytest.raises(HTTPException) as exc:
        po.create_order(po.POInput(data={'vendor':'Supplier'}),bad)
    assert exc.value.status_code==401
    lead=request(tmp_path,role='lead')
    with pytest.raises(HTTPException) as exc:
        po.create_order(po.POInput(data={'vendor':'Supplier','received_status':'Received'}),lead)
    assert exc.value.status_code==403
    # 5.51: leads may create a new PO supplier, but not edit supplier records.
    supplier=po.create_supplier(po.POInput(data={'name':'Test Supplier'}),lead)['item']
    assert supplier['name']=='Test Supplier'
    with pytest.raises(HTTPException) as exc:
        po.update_supplier(supplier['id'],po.POInput(data={'name':'Changed Supplier'}),lead)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        po.receive_po('pds','unknown',po.ReceiveInput(quantity=1),lead)
    assert exc.value.status_code==403
    tech=request(tmp_path,role='tech')
    with pytest.raises(HTTPException) as exc:
        po.create_order(po.POInput(data={'vendor':'Supplier'}),tech)
    assert exc.value.status_code==403


def test_pds_native_document_permissions_distinguish_roles(tmp_path):
    tech=request(tmp_path,role='tech')
    assert documents._document_permission(tech,None,'estimate','create')=='tech'
    assert documents._document_permission(tech,None,'estimate','edit')=='tech'
    assert documents._document_permission(tech,None,'invoice','create')=='tech'
    assert documents._document_permission(tech,None,'invoice','edit')=='tech'
    for kind,action in [('estimate','delete'),('invoice','delete')]:
        with pytest.raises(HTTPException) as exc:
            documents._document_permission(tech,None,kind,action)
        assert exc.value.status_code==403
    lead=request(tmp_path,role='lead')
    for kind in ('estimate','invoice'):
        assert documents._document_permission(lead,None,kind,'create')=='lead'
    with pytest.raises(HTTPException):
        documents._document_permission(lead,None,'invoice','delete')
    office=request(tmp_path,role='office')
    assert documents._document_permission(office,None,'invoice','delete')=='office'


def test_external_quickbooks_po_listed_by_job_without_posting(tmp_path):
    req=request(tmp_path,role='office',name='Office Admin')
    saved=asyncio.run(vault.create('pds',req,document_type='purchase_order',
        vendor='Supplier A',document_number='QB-15127',job_number='1126-15',
        notes='Original QuickBooks PO attached as reference',document_date='',po_number='',extracted_json='',library_scope='business',file=None))['item']
    assert saved['source']=='external'
    assert saved['document_number']=='QB-15127'
    assert saved['job_number']=='1126-15'
    assert saved['review_status']=='Saved - not posted'
    rows=vault.listing('pds',req,document_type='purchase_order',library_scope='business',job_number='1126-15')['items']
    assert [r['id'] for r in rows]==[saved['id']]
    assert vault.listing('pds',req,document_type='purchase_order',library_scope='business',job_number='other')['items']==[]
    assert not (tmp_path/'pds_purchase_orders'/'records.json').exists()
    assert not (tmp_path/'po_receiving').exists()
    assert not (tmp_path/'accounting').exists()


def test_external_reference_fields_are_role_limited(tmp_path):
    office=request(tmp_path,'office')
    for kind in ('estimate','invoice','purchase_order'):
        asyncio.run(vault.create('pds',office,document_type=kind,
            document_number='QB-'+kind,job_number='JOB',
            notes='Document',vendor='',document_date='',po_number='',extracted_json='',library_scope='business',file=None))
    lead=request(tmp_path,'lead')
    assert len(vault.listing('pds',lead,library_scope='business')['items'])==3
    tech=request(tmp_path,'tech')
    rows=vault.listing('pds',tech,library_scope='business')['items']
    assert [row['document_type'] for row in rows]==['estimate','invoice']
    with pytest.raises(HTTPException) as exc:
        vault.listing('pds',tech,library_scope='accounting')
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        asyncio.run(vault.create('pds',tech,document_type='purchase_order',notes='Not allowed',vendor='',document_number='',document_date='',po_number='',job_number='',extracted_json='',library_scope='business',file=None))
    assert exc.value.status_code==403


def test_ticket_and_saved_lists_expose_external_originals_and_creator():
    js=(ROOT/'static/app.js').read_text()
    assert 'pdsExternalReferences({jobNumber:String(job.job_number)})' in js
    assert 'pdsExternalReferences({type})' in js
    assert "pdsExternalReferences({type:'purchase_order'})" in js
    assert "'Created by '+item.created_by" in js
    assert 'External ' in js and 'Open Original' in js
    assert "alternateUpload.textContent='Alternate'" in js
    assert "const canCreatePO=['office','office_admin','admin','lead']" in js


def test_original_uploaded_po_is_retained_and_has_no_issued_po(tmp_path):
    from fastapi import UploadFile
    from io import BytesIO
    req=request(tmp_path,role='office',name='Office Clerk')
    uploaded=UploadFile(filename='QB_Purchase_Order_812.pdf',file=BytesIO(b'%PDF-1.4\n% PDS test attachment\n%%EOF'))
    item=asyncio.run(vault.create('pds',req,document_type='purchase_order',
        vendor='Supplier B',document_number='QB-812',document_date='2026-11-23',
        po_number='QB-812',job_number='1126-15',notes='Original QuickBooks order',
        extracted_json='',library_scope='business',file=uploaded))['item']
    folder=tmp_path/'document_vault'/'pds'
    saved=folder/'attachments'/item['attachment']
    assert saved.exists() and saved.read_bytes().startswith(b'%PDF')
    assert item['original_filename']=='QB_Purchase_Order_812.pdf'
    assert item['created_by']=='Office Clerk'
    assert not (tmp_path/'pds_purchase_orders'/'records.json').exists()
    assert not (tmp_path/'po_receiving').exists()
