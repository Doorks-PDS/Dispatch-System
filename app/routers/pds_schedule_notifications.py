"""Office-admin approval workflow for PDS Scheduler notification email."""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services import pds_schedule_notifications as notifications

router=APIRouter(prefix='/pds-schedule-notifications',tags=['pds-schedule-notifications'])

class Proposal(BaseModel):
    job_id:str
    recipient:str
    category:str
    subject:str
    message:str

class Decision(BaseModel):
    approve:bool

@router.get('/email/readiness')
def email_readiness(request:Request):
    return notifications.email_readiness(request)

@router.post('/email/proposals')
def propose(payload:Proposal,request:Request):
    return notifications.propose(request,payload.job_id,payload.recipient,payload.category,payload.subject,payload.message)

@router.get('/jobs/{job_id}/email-history')
def history(job_id:str,request:Request):
    return notifications.history(request,job_id)

@router.post('/email/proposals/{proposal_id}/decision')
def decide(proposal_id:str,payload:Decision,request:Request):
    return notifications.decide(request,proposal_id,payload.approve)
