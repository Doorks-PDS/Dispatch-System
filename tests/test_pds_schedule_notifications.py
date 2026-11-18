"""Scheduler notifications stay approval-backed and anchored to real PDS jobs."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.services import pds_schedule_notifications as notifications

class Jobs:
    def get_job(self, identity):
        if identity == 'job1':
            return {'id':'job1','email':'customer@example.com','customer':'Test Customer'}
        return None

def request(tmp_path, role='office_admin', platform='pds'):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path),calendar_store=Jobs())),
        state=SimpleNamespace(auth_user={'id':'reviewer'},auth_role=role),
        session={'active_platform':platform})

def proposal(req):
    return notifications.propose(req,'job1','customer@example.com','appointment',
                                 'Appointment update','Priority Door Systems: Appointment confirmed.')

def test_schedule_email_requires_verified_job_recipient_and_office_admin(tmp_path):
    r=request(tmp_path)
    for other in (request(tmp_path,role='tech'),request(tmp_path,platform='sdc')):
        with pytest.raises(HTTPException) as error:
            proposal(other)
        assert error.value.status_code==403
    with pytest.raises(HTTPException) as error:
        notifications.propose(r,'job1','wrong@example.com','appointment','Update','Priority Door Systems: Confirmed')
    assert error.value.status_code==409
    with pytest.raises(HTTPException):
        notifications.propose(r,'missing','customer@example.com','appointment','Update','Priority Door Systems: Confirmed')
    with pytest.raises(HTTPException):
        notifications.propose(r,'job1','customer@example.com','appointment','Update','No business identity')

def test_schedule_email_is_not_sent_until_explicit_approval(tmp_path):
    r=request(tmp_path)
    with patch('app.services.moses_email_transport.send_resend') as send:
        prepared=proposal(r)
        assert prepared['sent'] is False
        pid=prepared['proposal']['id']
        assert notifications.history(r,'job1')['items'][0]['status']=='pending'
        assert notifications.decide(r,pid,False)['status']=='rejected'
        with pytest.raises(HTTPException) as error:
            notifications.decide(r,pid,True)
        assert error.value.status_code==409
        send.assert_not_called()

def test_schedule_email_approval_is_hold_when_send_disabled(tmp_path):
    r=request(tmp_path)
    pid=proposal(r)['proposal']['id']
    with pytest.raises(HTTPException) as error:
        notifications.decide(r,pid,True)
    assert error.value.status_code==503
    assert notifications.history(r,'job1')['items'][0]['status']=='pending'

def test_schedule_email_uncertain_send_never_retries(tmp_path,monkeypatch):
    r=request(tmp_path)
    pid=proposal(r)['proposal']['id']
    monkeypatch.setenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED','true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    with patch('app.services.pds_schedule_notifications.ready'), patch('app.services.moses_email_transport.send_resend',side_effect=TimeoutError('provider uncertain')) as sender:
        with pytest.raises(HTTPException) as error:
            notifications.decide(r,pid,True)
        assert error.value.status_code==502
        with pytest.raises(HTTPException) as retry:
            notifications.decide(r,pid,True)
        assert retry.value.status_code==409
        assert sender.call_count==1
        assert notifications.history(r,'job1')['items'][0]['status']=='needs_review'

def test_schedule_email_provider_acceptance_not_delivery(tmp_path,monkeypatch):
    r=request(tmp_path)
    pid=proposal(r)['proposal']['id']
    monkeypatch.setenv('PDS_SCHEDULE_EMAIL_SEND_ENABLED','true')
    monkeypatch.setenv('MOSES_DOCUMENTS_FROM','NoReply@prioritydoors.com')
    with patch('app.services.pds_schedule_notifications.ready'), patch('app.services.moses_email_transport.send_resend',return_value='resend-test') as sender:
        result=notifications.decide(r,pid,True)
    assert sender.call_args.args[0]['to']=='customer@example.com'
    assert result['status']=='submitted' and result['delivered'] is False
    assert notifications.history(r,'job1')['items'][0]['status']=='submitted'

def test_identical_pending_email_proposals_are_reused(tmp_path):
    r = request(tmp_path)
    first = proposal(r)
    second = proposal(r)
    assert second['reused_pending'] is True
    assert first['proposal']['id'] == second['proposal']['id']
    assert len(notifications.history(r, 'job1')['items']) == 1


def test_distinct_email_contents_create_separate_proposals(tmp_path):
    r = request(tmp_path)
    first = proposal(r)
    second = notifications.propose(r,'job1','customer@example.com','appointment',
                                   'Appointment update','Priority Door Systems: Rescheduled.')
    assert second['reused_pending'] is False
    assert second['proposal']['id'] != first['proposal']['id']
    assert len(notifications.history(r, 'job1')['items']) == 2


def test_rejected_email_proposal_can_be_reprepared(tmp_path):
    r = request(tmp_path)
    first = proposal(r)
    notifications.decide(r, first['proposal']['id'], False)
    second = proposal(r)
    assert second['proposal']['id'] != first['proposal']['id']
    assert second['reused_pending'] is False
