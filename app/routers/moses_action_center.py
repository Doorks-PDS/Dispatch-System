"""Read-only source-backed action center for the same Moses agent and office UI.

No new data store, no cross-workspace aggregation, and no execution endpoints.
"""
from fastapi import APIRouter, Request
from app.services.moses_action_center import overview, pds_draft_detail

router = APIRouter(prefix='/moses-action-center', tags=['moses-action-center'])


@router.get('/overview')
def current_work(request: Request):
    return overview(request)


@router.get('/pds/drafts/{draft_id}')
def draft_detail(draft_id: str, request: Request):
    return pds_draft_detail(request, draft_id)


@router.get('/pds/jobs/{job_id}/context')
def job_context(job_id: str, request: Request):
    from app.services.moses_pds_job_context import inspect
    return inspect(request, job_id)

@router.get('/pds/document-emails/pending')
def pending_document_emails(request: Request):
    from app.services.moses_pds_document_actions import pending
    return pending(request)
