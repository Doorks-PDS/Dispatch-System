"""Invoice recipient policy: AP first, saved job contact second, workspace isolated."""
import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services.moses_delivery import preview
from app.routers.crm import CustomerCreate


def req(path, platform='doorks'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'u'}, auth_role='office_admin'),
                           session={'active_platform': platform},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=path)))


def seed(path, platform, collection, rows):
    directory=path/'business_workspaces'/platform
    directory.mkdir(parents=True, exist_ok=True)
    (directory/(collection+'.json')).write_text(json.dumps(rows))


def test_ap_overrides_invoice_contact(tmp_path):
    seed(tmp_path,'doorks','customers',[{'id':'c1','name':'ACME','invoice_email':'ap@acme.com','email':'office@acme.com'}])
    seed(tmp_path,'doorks','estimates_invoices',[{'id':'d1','document_type':'invoice','document_number':'JS00021','customer_id':'c1','contact_email':'job@acme.com'}])
    result=preview(req(tmp_path),'doorks','invoice','d1')
    assert result['to']=='ap@acme.com'
    assert result['recipient_source']=='customer_ap'
    assert result['sent'] is False and result['payment_created'] is False


def test_invoice_falls_back_to_job_contact(tmp_path):
    seed(tmp_path,'sdc','customers',[{'id':'c1','name':'ACME','email':'generic@acme.com'}])
    seed(tmp_path,'sdc','estimates_invoices',[{'id':'d1','document_type':'invoice','customer':'ACME','contact_email':'job@acme.com'}])
    result=preview(req(tmp_path,'sdc'),'sdc','invoice','d1')
    assert result['to']=='job@acme.com'
    assert result['recipient_source']=='job_contact'


def test_ambiguous_ap_does_not_guess(tmp_path):
    seed(tmp_path,'doorks','customers',[{'id':'c1','name':'ACME','invoice_email':'ap1@acme.com'}, {'id':'c2','name':'ACME','invoice_email':'ap2@acme.com'}])
    seed(tmp_path,'doorks','estimates_invoices',[{'id':'d1','document_type':'invoice','customer':'ACME','contact_email':'job@acme.com'}])
    with pytest.raises(HTTPException) as error:
        preview(req(tmp_path),'doorks','invoice','d1')
    assert error.value.status_code==409


def test_wrong_workspace_ap_never_used(tmp_path):
    seed(tmp_path,'sdc','customers',[{'id':'c1','name':'ACME','invoice_email':'secret@sdc.com'}])
    seed(tmp_path,'doorks','estimates_invoices',[{'id':'d1','document_type':'invoice','customer':'ACME','contact_email':'job@acme.com'}])
    assert preview(req(tmp_path),'doorks','invoice','d1')['to']=='job@acme.com'


def test_estimate_does_not_use_ap(tmp_path):
    seed(tmp_path,'doorks','customers',[{'id':'c1','name':'ACME','invoice_email':'ap@acme.com'}])
    seed(tmp_path,'doorks','estimates_invoices',[{'id':'d1','document_type':'estimate','document_number':'RE00076','customer_id':'c1','contact_email':'job@acme.com'}])
    assert preview(req(tmp_path),'doorks','estimate','d1')['to']=='job@acme.com'


def test_pds_customer_model_supports_invoice_email():
    item=CustomerCreate(company_name='ACME',email='job@acme.com',invoice_email='ap@acme.com')
    assert item.invoice_email=='ap@acme.com'


def test_pds_customer_invoice_email_persists_on_update(tmp_path):
    from app.services.crm_store import CRMStore
    store=CRMStore(tmp_path)
    saved=store.create_customer({'company_name':'AP TEST','email':'job@acme.com',
                                 'invoice_email':'ap@acme.com'})
    assert saved['invoice_email']=='ap@acme.com'
    updated=store.update_customer(saved['id'],{'invoice_email':'accounting@acme.com'})
    assert updated['email']=='job@acme.com'
    assert updated['invoice_email']=='accounting@acme.com'
    assert any(c['invoice_email']=='accounting@acme.com' for c in store.list_customers()
               if c['id']==saved['id'])
