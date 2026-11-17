"""Fail-safe policy for conversational AI recovery after tool/SDK errors.

This policy never executes or prepares business actions. A second AI call is
allowed only when no side-effect proposal was recorded for this request.
"""
from __future__ import annotations


def may_retry_read_only(exc: Exception, request) -> bool:
    """Refuse recovery after partial action preparation or authorization errors."""
    if getattr(request.state, 'moses_action_proposals', None):
        return False
    if getattr(request.state, 'moses_document_proposals', None):
        return False
    # Authorization errors must not be treated as a model outage.
    status = getattr(exc, 'status_code', None)
    if isinstance(status, int) and status in (400, 401, 403, 404, 409, 422):
        return False
    return True
