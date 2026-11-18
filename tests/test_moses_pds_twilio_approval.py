from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services import moses_pds_twilio as sms
from app.services.pds_sms_consent import handle_keyword

class JobStore:
    def get_job(self, ident):
        if ident == 'job1':
            return {'id':'job1','phone':'+17605550111'}
        return None

def req(tmp_path, role='office_admin', workspace='pds'):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path),calendar_store=JobStore())),
                           state=SimpleNamespace(auth_user={'id':'admin'},auth_role=role),
                           session={'active_platform':workspace})

def consent(tmp_path):
    handle_keyword(tmp_path, '+17605550111', 'SM-start', 'START',privacy_url='https://example.com/privacy',terms_url='https://example.com/terms')
    handle_keyword(tmp_path, '+17605550111', 'SM-yes', 'YES',privacy_url='https://example.com/privacy',terms_url='https://example.com/terms')

def test_sms_approval_guards(tmp_path):
    r=req(tmp_path)
    with pytest.raises(HTTPException):
        sms.propose(r, 'job1','+17605550111','Priority Door Systems: ETA 2pm')
    consent(tmp_path)
    with pytest.raises(HTTPException):
        sms.propose(r,'job1','+17605550112','Priority Door Systems: ETA 2pm')
    with pytest.raises(HTTPException):
        sms.propose(req(tmp_path,'tech'),'job1','+17605550111','Priority Door Systems: ETA 2pm')
    with pytest.raises(HTTPException):
        sms.propose(req(tmp_path,workspace='sdc'),'job1','+17605550111','Priority Door Systems: ETA 2pm')

def test_sms_pending_decline_and_no_double_send(tmp_path):
    consent(tmp_path)
    r=req(tmp_path)
    entry=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    pid=entry['proposal']['id']
    assert sms.pending(r)['proposals'][0]['id']==pid
    assert sms.decide(r,pid,False)['status']=='rejected'
    with pytest.raises(HTTPException) as exc:
        sms.decide(r,pid,True)
    assert exc.value.status_code==409

def test_sms_approval_revoked_consent_blocks_send(tmp_path, monkeypatch):
    consent(tmp_path)
    r=req(tmp_path)
    pid=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')['proposal']['id']
    handle_keyword(tmp_path,'+17605550111','SM-stop','STOP',privacy_url='https://example.com/privacy',terms_url='https://example.com/terms')
    monkeypatch.setenv('PDS_SMS_SEND_ENABLED','true')
    with pytest.raises(HTTPException) as exc:
        sms.decide(r,pid,True)
    assert exc.value.status_code==409
    assert sms.receipt(r,pid)['status']=='pending'

def test_sms_ambiguous_send_never_retries(tmp_path, monkeypatch):
    consent(tmp_path)
    r=req(tmp_path)
    pid=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')['proposal']['id']
    monkeypatch.setenv('PDS_SMS_SEND_ENABLED','true')
    monkeypatch.setenv('TWILIO_ACCOUNT_SID','AC'+'1'*32)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN','testtoken')
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL','https://example.org')
    monkeypatch.setenv('PDS_TWILIO_NUMBER','+17606421131')
    with patch('requests.post',side_effect=TimeoutError('uncertain')) as sender:
        with pytest.raises(HTTPException) as exc:
            sms.decide(r,pid,True)
        assert exc.value.status_code==502
        assert sender.call_count==1
        with pytest.raises(HTTPException) as second:
            sms.decide(r,pid,True)
        assert second.value.status_code==409
        assert sender.call_count==1
    assert sms.receipt(r,pid)['status']=='needs_review'

def test_sms_delivery_status_is_not_automatic_claim(tmp_path, monkeypatch):
    consent(tmp_path)
    r=req(tmp_path)
    pid=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')['proposal']['id']
    monkeypatch.setenv('PDS_SMS_SEND_ENABLED','true')
    monkeypatch.setenv('TWILIO_ACCOUNT_SID','AC'+'1'*32)
    monkeypatch.setenv('TWILIO_AUTH_TOKEN','testtoken')
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL','https://example.org')
    monkeypatch.setenv('PDS_TWILIO_NUMBER','+17606421131')
    monkeypatch.setenv('PDS_SMS_PUBLIC_BASE_URL','https://example.org')
    response=SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'sid':'SM'+'2'*32})
    with patch('requests.post',return_value=response) as sender:
        result=sms.decide(r,pid,True)
    assert sender.call_args.kwargs['data']['StatusCallback']=='https://example.org/pds/sms/twilio/status?proposal_id='+pid
    assert result['status']=='submitted' and result['delivered'] is False
    assert sms.reconcile_status(tmp_path,'SM'+'2'*32,'delivered')
    assert sms.receipt(r,pid)['status']=='delivered'
    assert sms.reconcile_status(tmp_path,'SM'+'2'*32,'queued')
    assert sms.receipt(r,pid)['status']=='delivered'


def test_identical_pending_sms_proposals_reuse_one_approval(tmp_path):
    consent(tmp_path)
    r=req(tmp_path)
    first=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    second=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    assert first['reused_pending'] is False
    assert second['reused_pending'] is True
    assert first['proposal']['id'] == second['proposal']['id']
    assert len(sms.job_history(r,'job1')['items']) == 1

def test_different_sms_or_rejected_sms_get_separate_approvals(tmp_path):
    consent(tmp_path)
    r=req(tmp_path)
    first=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    different=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 3pm')
    assert different['proposal']['id'] != first['proposal']['id']
    assert different['reused_pending'] is False
    sms.decide(r,first['proposal']['id'],False)
    retried=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    assert retried['proposal']['id'] != first['proposal']['id']
    assert retried['reused_pending'] is False
    assert len(sms.job_history(r,'job1')['items']) == 3


def test_sms_approval_blocks_stale_job_phone_after_contact_change(tmp_path, monkeypatch):
    consent(tmp_path)
    r=req(tmp_path)
    proposal=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')
    pid=proposal['proposal']['id']
    monkeypatch.setenv('PDS_SMS_SEND_ENABLED','true')
    with patch.object(r.app.state.calendar_store, 'get_job', return_value={
            'id':'job1','phone':'+17605550999'}):
        with pytest.raises(HTTPException) as error:
            sms.decide(r,pid,True)
    assert error.value.status_code==409
    assert sms.receipt(r,pid)['status']=='pending'


def test_early_signed_callback_reconciles_before_provider_response(tmp_path, monkeypatch):
    consent(tmp_path)
    r = req(tmp_path)
    pid = sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')['proposal']['id']
    for name, value in {'PDS_SMS_SEND_ENABLED':'true','TWILIO_ACCOUNT_SID':'AC'+'1'*32,
                        'TWILIO_AUTH_TOKEN':'testtoken','PDS_SMS_PUBLIC_BASE_URL':'https://example.org',
                        'PDS_TWILIO_NUMBER':'+17606421131'}.items():
        monkeypatch.setenv(name,value)
    sid='SM'+'3'*32
    def early_response(*args, **kwargs):
        assert kwargs['data']['StatusCallback'].endswith('proposal_id='+pid)
        assert sms.reconcile_status(tmp_path,sid,'delivered',pid)
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'sid':sid})
    with patch('requests.post',side_effect=early_response):
        result=sms.decide(r,pid,True)
    assert result['status']=='delivered' and result['delivered'] is True
    assert sms.receipt(r,pid)['status']=='delivered'
    assert sms.reconcile_status(tmp_path,sid,'queued',pid)
    assert sms.receipt(r,pid)['status']=='delivered'

def test_signed_callback_cannot_claim_unapproved_or_mismatched_proposal(tmp_path):
    consent(tmp_path)
    r=req(tmp_path)
    first=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 2pm')['proposal']['id']
    second=sms.propose(r,'job1','+17605550111','Priority Door Systems: ETA 3pm')['proposal']['id']
    sid='SM'+'4'*32
    assert not sms.reconcile_status(tmp_path,sid,'delivered',first)
    with sms._db(r) as db:
        db.execute("UPDATE proposals SET status='needs_review' WHERE id=?",(first,))
    assert not sms.reconcile_status(tmp_path,sid,'delivered',second)
    assert sms.reconcile_status(tmp_path,sid,'delivered',first)
    assert not sms.reconcile_status(tmp_path,sid,'failed',second)
    assert sms.receipt(r,first)['status']=='delivered'
    assert sms.receipt(r,second)['status']=='pending'
