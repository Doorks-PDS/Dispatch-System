"""Route an authorized, specific PDS quote request into Moses's existing tools.

The caller must already have verified the active PDS workspace and office_admin role.
The deterministic broad job queues execute before this helper is called.
"""
from __future__ import annotations

import logging
from typing import Any, Optional


def dispatch(request: Any, message: str, history: list) -> Optional[dict]:
    # Defend in depth: never expose the SDK workflow outside PDS office_admin.
    if getattr(request.state, 'auth_role', None) != 'office_admin':
        return None
    if (getattr(request, 'session', {}) or {}).get('active_platform') != 'pds':
        return None
    from app.services.moses_agent import enabled
    if not enabled('pds'):
        return None  # Maintain the pre-existing read-only fallback.
    request.state.moses_action_proposals = []
    request.state.moses_document_proposals = []
    try:
        from app.services.moses_agent import answer
        response = answer(request, message, history)
    except Exception as exc:
        logging.getLogger(__name__).error(
            'Moses verified PDS quote conversation failed exception_type=%s',
            type(exc).__name__)
        return {
            'answer': ('Moses could not confirm the quote preparation. Review saved drafts and '
                       'pending approvals before retrying; no completion is confirmed.'),
            'workspace': 'pds', 'matches': [], 'navigation': [],
            'agent_connected': False, 'action_proposals': [], 'document_proposals': [],
        }
    return {
        'answer': response, 'workspace': 'pds', 'matches': [],
        'navigation': [{'label': 'Open All Jobs', 'target': 'all_jobs'},
                       {'label': 'Open Estimates', 'target': 'estimates'}],
        'action_proposals': getattr(request.state, 'moses_action_proposals', []),
        'document_proposals': getattr(request.state, 'moses_document_proposals', []),
        'agent_connected': True,
    }
