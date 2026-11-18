from types import SimpleNamespace
from fastapi import HTTPException
import pytest
from app.services import moses_pds_invoice_plan as invoices

class Jobs:
    def __init__(self):
        self.rows=[{'id':'a1','job_number':'1126-01','customer':'Customer A','status':'To Be Invoiced'},
                   {'id':'a2','job_number':'1126-02','customer':'Customer B','status':'To Be Invoiced','invoice_number':'JS00030'}]
    def list_jobs(self):return self.rows
    def get_job(self,id):return next((j for j in self.rows if j['id']==id),None)
class Docs:
    def list_documents(self,**kwargs):return []
def req(tmp_path,role='office_admin',space='pds'):
    return SimpleNamespace(state=SimpleNamespace(auth_user={'id':'user'},auth_role=role),
                           session={'active_platform':space},
                           app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path),calendar_store=Jobs(),documents_store=Docs())))

def test_invoice_packet_is_idempotent_and_does_not_create_invoice(tmp_path):
    r=req(tmp_path)
    review=invoices.inspect(r,'a1')
    assert review['ready_for_manual_review']
    assert review['official_invoice_created'] is False
    assert invoices.inspect(r,'a2')['ready_for_manual_review'] is False
    first=invoices.prepare(r)
    assert first['count']==1 and first['official_invoices_created']==0
    second=invoices.prepare(r)
    assert second['count']==1 and second['saved_review_packets'][0]['existing'] is True
    assert len(invoices.receipts(r)['receipts'])==1

def test_invoice_packet_security(tmp_path):
    with pytest.raises(HTTPException): invoices.inspect(req(tmp_path,space='sdc'),'a1')
    with pytest.raises(HTTPException): invoices.prepare(req(tmp_path,role='tech'))
    with pytest.raises(HTTPException): invoices.inspect(req(tmp_path),'../a1')
