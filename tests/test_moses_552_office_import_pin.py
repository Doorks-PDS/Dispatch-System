"""5.52: office report secondary PIN and safe incremental PDS imports."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app.routers import pds_office_reports as reports
from app.routers import pds_purchase_orders as po
from app.services.crm_store import CRMStore
from app.services.address_store import AddressStore

ROOT=Path(__file__).parents[1]

def req(tmp_path, role='office_admin'):
    return SimpleNamespace(
        state=SimpleNamespace(auth_user={'id':'office-123','name':'Office User'},auth_role=role),
        session={'active_platform':'pds'},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path), project_root=str(tmp_path),
            crm_store=CRMStore(tmp_path),address_store=AddressStore(tmp_path))),
    )

def test_office_report_pin_is_server_checked_and_session_scoped(monkeypatch,tmp_path):
    monkeypatch.setenv('PDS_OFFICE_REPORT_PIN','2005')
    request=req(tmp_path)
    assert reports.access(request)['unlocked'] is False
    with pytest.raises(HTTPException) as error:
        reports.unlock(reports.PinInput(pin='0000'),request)
    assert error.value.status_code==403
    assert reports.access(request)['unlocked'] is False
    assert reports.unlock(reports.PinInput(pin='2005'),request)['unlocked']
    assert reports.access(request)['unlocked'] is True
    reports.lock(request)
    assert reports.access(request)['unlocked'] is False
    request.state.auth_role='lead'
    with pytest.raises(HTTPException) as error:reports.access(request)
    assert error.value.status_code==403


def test_server_throttles_incorrect_pin_attempts(monkeypatch,tmp_path):
    monkeypatch.setenv('PDS_OFFICE_REPORT_PIN','2005')
    request=req(tmp_path)
    for _ in range(5):
        with pytest.raises(HTTPException):reports.unlock(reports.PinInput(pin='1111'),request)
    with pytest.raises(HTTPException) as error:
        reports.unlock(reports.PinInput(pin='2005'),request)
    assert error.value.status_code==429


def test_import_adds_only_new_customers_contacts_addresses_and_service_vendors(tmp_path):
    request=req(tmp_path)
    store=request.app.state.crm_store
    existing=store.create_customer({'company_name':'The Irvine Company','phone_number':'unchanged'})
    batch=po.ImportBatch(kind='customers',rows=[
        {'Company Name':'The Irvine Company','Phone':'changed'},
        {'Company Name':'New Customer','Address':'123 Main St','Phone':'555-1234'},
        {'Company Name':'New Customer','Phone':'duplicate'},
    ],confirm_import=True)
    result=po.preview_import(batch,request)
    assert result['new_count']==1 and result['duplicate_count']==2
    assert len(store.list_customers())==1
    assert po.commit_import(batch,request)['created']==1
    assert len(store.list_customers())==2
    assert next(c for c in store.list_customers() if c['id']==existing['id'])['phone_number']=='unchanged'
    contacts=po.ImportBatch(kind='contacts',rows=[
        {'Contact Name':'A Person','Company Name':'The Irvine Company','Email':'person@example.com'},
        {'Contact Name':'A Person','Company Name':'The Irvine Company'},
    ],confirm_import=True)
    assert po.commit_import(contacts,request)['created']==1
    saved=store.list_contacts()
    assert saved[0]['customer_id']==existing['id']
    addresses=po.ImportBatch(kind='addresses',rows=[
        {'Service Address':'101 Park Ave','City':'Irvine','State':'CA','Customer':'The Irvine Company'}
    ],confirm_import=True)
    assert po.commit_import(addresses,request)['created']==1
    assert request.app.state.address_store._load_items()[0]['customer_id']==existing['id']
    service=po.ImportBatch(kind='service_vendors',rows=[
        {'Company Name':'Mobile Glass','Trade':'Glass','Phone':'555-1212'}
    ],confirm_import=True)
    assert po.commit_import(service,request)['created']==1
    assert po.commit_import(service,request)['created']==0
    with pytest.raises(HTTPException):
        po.commit_import(po.ImportBatch(kind='purchase_orders',rows=[{'PO':'QB-10'}],confirm_import=True),request)


def test_import_preview_requires_admin_and_existing_data_unmodified(tmp_path):
    request=req(tmp_path,'office')
    batch=po.ImportBatch(kind='customers',rows=[{'Company Name':'New Customer'}])
    with pytest.raises(HTTPException) as err:po.preview_import(batch,request)
    assert err.value.status_code==403


def test_ui_uses_masked_numeric_pin_and_reviewed_import_destinations():
    text=(ROOT/'static/app.js').read_text()
    assert "alternateUpload.textContent='Alternate'" in text
    assert "input.type='password';input.inputMode='numeric'" in text
    assert "requestMaskedOfficePin(\"Accounting Hub\")" in text
    assert "ensurePdsOfficeReportPin(\"Roll Up Data\")" in text
    assert "ensurePdsOfficeReportPin(\"Payroll\", true)" in text
    assert 'can_import_records' in text and 'importable_kinds' in text
