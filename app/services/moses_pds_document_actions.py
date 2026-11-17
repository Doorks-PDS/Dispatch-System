"""Conversational access to the existing verified PDS Resend approval ledger.

No new sender. No autonomous approvals or provider calls. Uses the exact
saved PDS estimate/invoice number and current office authorization.
"""
from __future__ import annotations

import re
from fastapi import HTTPException


def _guard(request):
    from app.services import moses_pds_document_email as delivery
    delivery._guard(request)
    return delivery


def _identifier(kind, number):
    if kind not in ('estimate', 'invoice'):
        raise HTTPException(422, 'Choose estimate or invoice')
    prefix = 'RE' if kind == 'estimate' else 'JS'
    if not isinstance(number, str) or not re.fullmatch(prefix + r'[0-9]{5,}', number, re.I):
        raise HTTPException(422, 'Enter an exact saved PDS document number')
    return number.upper()


def review(request, kind, number):
    delivery = _guard(request)
    number = _identifier(kind, number)
    preview = delivery.preview(request, kind, number)
    history = delivery.history(request, kind, number)
    if not isinstance(preview, dict) or not isinstance(history, list):
        raise HTTPException(503, 'Document delivery ledger returned invalid data')
    return {'workspace': 'pds', 'document': preview,
            'history': history[-12:], 'read_only': True,
            'message': 'Official saved document and recipient verified. No email sent.'}


def prepare(request, kind, number):
    delivery = _guard(request)
    number = _identifier(kind, number)
    outcome = delivery.propose(request, kind, number)
    proposal = outcome.get('proposal') if isinstance(outcome, dict) else None
    if not isinstance(proposal, dict) or not re.fullmatch(r'[a-f0-9]{32}', str(proposal.get('id') or '')):
        raise HTTPException(503, 'Saved email approval could not be verified')
    safe = {k: proposal.get(k) for k in ('id','state','kind','number','job_number','to',
            'from','subject','filename','sent')}
    safe['kind'] = 'pds_document_email'
    safe['document_kind'] = kind
    safe['approval_required'] = True
    safe['sent'] = False
    existing = getattr(request.state, 'moses_document_proposals', None)
    if isinstance(existing, list):
        existing.append(safe)
    return {'proposal': safe, 'approval_required': True, 'sent': False,
            'next_step': 'Review the exact recipient and PDF and approve or reject the pending email card.'}


def pending(request):
    delivery = _guard(request)
    path = delivery._file(request)
    # Read-only; the original service owns the durable ledger and file lock.
    with delivery._locked(path):
        rows = delivery._load(path)
    if not isinstance(rows, list):
        raise HTTPException(503, 'Document email approval ledger unavailable')
    proposals = []
    for row in rows:
        if row.get('state') != 'pending':
            continue
        item = delivery._public(row)
        proposals.append({'id': item['id'], 'state': item['state'], 'kind': 'pds_document_email',
                          'document_kind': item['kind'], 'number': item['number'],
                          'job_number': item['job_number'], 'to': item['to'], 'from': item['from'],
                          'subject': item['subject'], 'filename': item['filename'],
                          'approval_required': True, 'sent': False})
    return {'workspace': 'pds', 'proposals': proposals[-30:], 'count': len(proposals),
            'note': 'Approval only. No messages were sent.'}
