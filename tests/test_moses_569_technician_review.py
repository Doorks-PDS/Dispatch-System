"""Rev 5.69: technicians create estimates/invoices, office approves and sends.

Never performs network calls or edits production data.
"""
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.services import moses_pds_document_email as delivery
from app.routers import documents


def context(tmp_path, role='tech', kind='estimate'):
    folder=tmp_path/'documents'; folder.mkdir()
    number='RE00077' if kind=='estimate' else 'JS00077'
    (folder/(number+'.pdf')).write_bytes(b'%PDF-1.5\nreview-only sample')
    doc={'type':kind,'number':number,'filename':number+'.pdf','job_id':'job-A',
         'job_number':'1126-77','customer':'Review Test Company'}
    job={'id':'job-A','job_number':'1126-77','customer':'Review Test Company',
         'status':'Quote' if kind=='estimate' else 'Complete','contact_email':'customer@example.com'}
    class Jobs:
        def list_jobs(self):return [job]
        def get_job(self,id):return job if id==job['id'] else None
        def update_job(self,id,updates):job.update(updates);return job
    req=SimpleNamespace(state=SimpleNamespace(auth_role=role,auth_user={'id':role}),
        session={'active_platform':'pds'},app=SimpleNamespace(state=SimpleNamespace(
            data_dir=tmp_path,documents_store=SimpleNamespace(dir=folder,list_documents=lambda:[doc]),
            calendar_store=Jobs(),require_key=lambda key, request=None:req.state.auth_role)))
    return req,job,doc


def mail_identity(*args):
    return {'issues':[],'from':'NoReply@prioritydoors.com',
            'reply_to':'Estimates@prioritydoors.com','cc':''}


def test_technician_proposes_but_cannot_send_or_read_office_queue(tmp_path,monkeypatch):
    req,job,doc=context(tmp_path)
    monkeypatch.setattr(delivery,'identity',mail_identity)
    number=doc['number']
    assert delivery.preview(req,'estimate',number)['requires_office_review'] is True
    result=delivery.propose(req,'estimate',number)
    proposal=result['proposal']
    assert proposal['requested_role']=='tech'
    assert proposal['ready_label']=='Quote Ready'
    assert proposal['requires_office_review'] is True
    assert delivery.propose(req,'estimate',number)['proposal']['id']==proposal['id']
    assert job['status']=='Quote'
    with pytest.raises(HTTPException) as exc:delivery.decide(req,proposal['id'],True)
    assert exc.value.status_code==403
    assert job['status']=='Quote'
    with pytest.raises(HTTPException) as exc:delivery.review_queue(req)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:documents._document_permission(req,None,'purchase_order','create')
    assert exc.value.status_code==403
    assert documents._document_permission(req,None,'estimate','create')=='tech'
    assert documents._document_permission(req,None,'invoice','edit')=='tech'


def test_lead_unchanged_but_cannot_approve_tech_draft(tmp_path,monkeypatch):
    req,job,doc=context(tmp_path)
    monkeypatch.setattr(delivery,'identity',mail_identity)
    pid=delivery.propose(req,'estimate',doc['number'])['proposal']['id']
    req.state.auth_role='lead';req.state.auth_user={'id':'lead'}
    with pytest.raises(HTTPException) as exc:delivery.review_queue(req)
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:delivery.decide(req,pid,True)
    assert exc.value.status_code==403
    # Existing leads retain their independent document sending permissions.
    assert delivery.preview(req,'estimate',doc['number'])['requires_office_review'] is False
    assert documents._document_permission(req,None,'estimate','create')=='lead'


def test_office_review_and_send_via_existing_resend(tmp_path,monkeypatch):
    from app.services import moses_email_transport
    req,job,doc=context(tmp_path)
    monkeypatch.setattr(delivery,'identity',mail_identity)
    pid=delivery.propose(req,'estimate',doc['number'])['proposal']['id']
    req.state.auth_role='office';req.state.auth_user={'id':'office'}
    queue=delivery.review_queue(req)
    assert queue['count']==1 and queue['items'][0]['number']==doc['number']
    seen=[]
    monkeypatch.setenv('MOSES_PDS_DOCUMENT_SEND_ENABLED','true')
    monkeypatch.setattr(moses_email_transport,'ready',lambda sender:seen.append(('ready',sender)))
    monkeypatch.setattr(moses_email_transport,'send_resend_attachment',lambda *a,**kw:seen.append(('send',a[0]['to'])) or 'resend-1')
    result=delivery.decide(req,pid,True)
    assert result['state']=='sent' and result['sent']
    assert seen[1]==('send','customer@example.com')
    assert job['status']=='Quote Sent'
    assert delivery.review_queue(req)['count']==0


def test_edit_after_review_makes_request_stale_no_send(tmp_path,monkeypatch):
    from app.services import moses_email_transport
    req,job,doc=context(tmp_path,kind='invoice')
    monkeypatch.setattr(delivery,'identity',mail_identity)
    pid=delivery.propose(req,'invoice',doc['number'])['proposal']['id']
    assert delivery.review_queue is not None
    req.state.auth_role='office_admin';req.state.auth_user={'id':'admin'}
    assert delivery.review_queue(req)['items'][0]['ready_label']=='Invoice Ready'
    (req.app.state.documents_store.dir/(doc['number']+'.pdf')).write_bytes(b'%PDF-1.6\nchanged')
    monkeypatch.setenv('MOSES_PDS_DOCUMENT_SEND_ENABLED','true')
    monkeypatch.setattr(moses_email_transport,'send_resend_attachment',lambda *a,**kw:pytest.fail('Must not send a modified PDF'))
    with pytest.raises(HTTPException) as exc:delivery.decide(req,pid,True)
    assert exc.value.status_code==409
    assert job['status']=='Complete'


def test_ui_has_ready_for_review_not_technician_po():
    root=Path(__file__).resolve().parents[1]
    js=(root/'static/app.js').read_text()
    center=(root/'static/moses_action_center.js').read_text()
    assert 'Submit for Office Review' in js
    assert 'if(preview.send_enabled===false && preview.requires_office_review !== true)' in js
    assert "if (technicianReview)" in js
    assert "'__REVIEW__'" in js
    assert "['review','Ready for Review']" in js
    assert 'moses-open-pds-document-review' in center
    assert 'Tech' not in center or 'purchase order' not in center.lower()
