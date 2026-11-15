"""Production-code briefing tests; use synthetic records and temporary storage only."""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.moses_briefing import brief, summary


def req(tmp_path, platform='pds', role='office_admin', jobs=None):
    store = SimpleNamespace(list_jobs=lambda: jobs if jobs is not None else [])
    return SimpleNamespace(state=SimpleNamespace(auth_user='synthetic-admin', auth_role=role),
        session={'active_platform': platform},
        app=SimpleNamespace(state=SimpleNamespace(data_dir=tmp_path, calendar_store=store)))


def write(tmp_path, platform, name, data):
    folder = tmp_path / 'business_workspaces' / platform
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (name + '.json')).write_text(json.dumps(data), encoding='utf-8')


def test_pds_saved_records_and_privacy(tmp_path):
    records = [
        {'id':'1','customer':'Irvine Company','job_number':'1126-01', 'status':'To Be Quoted', 'private_token':'HIDDEN'},
        {'id':'2','customer':'Acme','job_number':'1126-02','status':'To Be Invoiced','job_notes':'CONFIDENTIAL'},
    ]
    report=brief(req(tmp_path,jobs=records))
    assert report['workspace']=='pds' and report['queues']['needs_quote']['count']==1
    assert report['queues']['needs_invoice']['count']==1
    assert not report['records_changed'] and report['read_only']
    assert 'HIDDEN' not in str(report) and 'CONFIDENTIAL' not in str(report)
    assert 'Irvine Company' in summary(report)
    assert not list(tmp_path.iterdir())


def test_doorks_work_queue_and_po(tmp_path):
    write(tmp_path,'doorks','work_orders',[{'id':'d1','customer':'A','status':'To Be Quoted'},
                                            {'id':'d2','customer':'B','status':'To Be Invoiced'}])
    write(tmp_path,'doorks','purchase_orders',[{'id':'p1','status':'Ordered','private_token':'HIDDEN'}])
    report=brief(req(tmp_path,'doorks'))
    assert report['queues']['needs_quote']['count']==1
    assert report['queues']['po_open']['count']==1
    assert 'HIDDEN' not in str(report)


def test_sdc_leads_orders_invoice_type_separation(tmp_path):
    write(tmp_path,'sdc','software_leads',[{'id':'l1','company':'Example LLC','status':'New', 'email':'PRIVATE_EMAIL'}])
    write(tmp_path,'sdc','orders',[{'id':'o1','status':'Open'}])
    write(tmp_path,'sdc','estimates_invoices',[{'id':'e1','document_type':'Estimate','status':'Sent'},
                                               {'id':'i1','document_type':'Invoice','status':'Sent'}])
    report=brief(req(tmp_path,'sdc'))
    assert report['queues']['leads_new']['count']==1
    assert report['queues']['orders_open']['count']==1
    assert report['queues']['unpaid_invoices']['count']==1
    assert 'PRIVATE_EMAIL' not in str(report)


def test_security_and_missing_or_corrupt_records(tmp_path):
    for platform, role in [('pds','technician'), ('doorks','technician'), ('invalid','office_admin')]:
        with pytest.raises(HTTPException) as err: brief(req(tmp_path,platform,role))
        assert err.value.status_code==403
    with pytest.raises(HTTPException) as err: brief(req(tmp_path,'doorks'))
    assert err.value.status_code==503
    folder=tmp_path/'business_workspaces'/'doorks'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'work_orders.json').write_text('{broken',encoding='utf-8')
    with pytest.raises(HTTPException) as err: brief(req(tmp_path,'doorks'))
    assert err.value.status_code==503
