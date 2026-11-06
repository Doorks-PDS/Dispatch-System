import io
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.routers import doorks_portals as portal

def test_vendor_pdf_contains_document_content():
    data={'document_type':'estimate','work_order_number':'1126-02','reference':'V-10',
          'amount':125.0,'line_items':[{'description':'Door closer adjustment','quantity':2,'rate':62.5}]}
    pdf=portal._vendor_pdf_bytes(data,'Sample Vendor').getvalue()
    assert pdf.startswith(b'%PDF-') and len(pdf)>1200

def test_vendor_pdf_is_scoped_to_account():
    req=SimpleNamespace()
    with patch.object(portal,'_vendor_user',return_value={'vendor_id':'v1','company':'Vendor One'}),\
         patch.object(portal,'store',return_value='ignored'),\
         patch.object(portal,'read',return_value={'vendor_commercial_documents':[{'id':'d1','vendor_id':'v2'}]}):
        with pytest.raises(HTTPException) as err:
            portal.vendor_commercial_pdf('d1',req)
        assert err.value.status_code==404

def test_reminder_deduplication(tmp_path):
    from datetime import timedelta
    expiration=(portal.now().date()+timedelta(days=5)).isoformat()
    req=SimpleNamespace()
    path=tmp_path/'portal.json'
    portal.write(path,{'invites':[],'submissions':[{'id':'s1','source_record_type':'vendor_profile',
        'status':'approved','expires_on':expiration,'compliance_type':'Insurance','record_id':'v1'}],
        'notifications':[]})
    with patch.object(portal,'admin'),patch.object(portal,'store',return_value=path):
        first=portal.generate_compliance_reminders(req)
        second=portal.generate_compliance_reminders(req)
    assert first['created']==1 and second['created']==0
