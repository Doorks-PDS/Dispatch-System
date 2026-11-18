"""Office-only PDS SMS approval cards. No anonymous sending routes."""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services import moses_pds_twilio as sms

router = APIRouter(prefix='/moses-action-center/pds/sms',tags=['moses-pds-sms'])

class Draft(BaseModel):
    job_id: str
    phone: str
    message: str

class Decision(BaseModel):
    approve: bool

@router.post('/proposals')
def propose(payload:Draft,request:Request):
    return sms.propose(request,payload.job_id,payload.phone,payload.message)

@router.get('/proposals')
def pending(request:Request):
    return sms.pending(request)

@router.get('/jobs/{job_id}/history')
def job_history(job_id:str,request:Request):
    return sms.job_history(request,job_id)

@router.get('/proposals/{proposal_id}')
def receipt(proposal_id:str,request:Request):
    return sms.receipt(request,proposal_id)

@router.post('/proposals/{proposal_id}/decision')
def decide(proposal_id:str,payload:Decision,request:Request):
    return sms.decide(request,proposal_id,payload.approve)
