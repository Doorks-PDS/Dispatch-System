"""Verified conversational action follow-ups. No stored chat authority or business writes.

Chat supplies only an action *reference*. Every claim is re-read from the scoped
existing proposal ledger; an action cannot be approved by this helper.
"""
from __future__ import annotations

import re
from fastapi import HTTPException

_ACTION_KINDS = frozenset((
    'job_status', 'order_status', 'schedule', 'new_work_order',
    'estimate_draft', 'estimate_to_invoice', 'purchase_order',
    'catalog_part', 'receiving', 'supplier_bill',
))
_STATUS_QUESTION = re.compile(
    r'\b(?:did (?:it|that|the action) (?:work|go through|complete|finish|save)|'
    r'was (?:it|that) (?:approved|saved|completed|done)|'
    r'what (?:happened|was the result|is the status)|'
    r'where (?:are we|did we leave off)|'
    r'(?:check|verify|confirm) (?:that|the|my|last) (?:action|approval|change)|'
    r'(?:is|has) (?:it|that) (?:done|finished|complete|completed)|'
    r'what(?:\x27s| is) next|next step|what should (?:we|i) do next)\b', re.I,
)


def followup(request, message: str, context: dict | None) -> dict | None:
    """Return a grounded answer only for explicit status/next-step intent.

    Unsupported/unknown references stop safely. This is not fuzzy record lookup.
    """
    if not isinstance(message, str) or not _STATUS_QUESTION.search(message):
        return None
    if not isinstance(context, dict) or not context:
        return None
    if set(context) != {'kind', 'proposal_id', 'workspace'}:
        return {'answer': 'That action reference is invalid. Open Moses approvals to select a saved action.',
                'action_verified': False, 'read_only': True}
    kind, pid, platform = (context[k] for k in ('kind', 'proposal_id', 'workspace'))
    if (not isinstance(kind, str) or kind not in _ACTION_KINDS or
            not isinstance(pid, str) or not re.fullmatch(r'[a-f0-9]{32}', pid) or
            platform not in ('pds', 'doorks', 'sdc')):
        return {'answer': 'That action reference is invalid. Open Moses approvals to select a saved action.',
                'action_verified': False, 'read_only': True}
    from app.services.moses_butler_flow import _scope, receipt
    current = _scope(request)  # Login, office-admin, active workspace
    if current != platform:
        return {'answer': 'That action belongs to another workspace. Select the correct workspace and action first.',
                'action_verified': False, 'read_only': True}
    try:
        saved = receipt(request, kind, pid)
    except HTTPException as exc:
        if exc.status_code in (403, 401):
            raise
        return {'answer': 'I could not verify that action in the saved approvals. Please open the approval history; I have not changed anything.',
                'action_verified': False, 'read_only': True}
    if not isinstance(saved, dict) or saved.get('proposal_id') != pid or saved.get('workspace') != current:
        return {'answer': 'The saved action receipt did not match the selected action. Manual review is required.',
                'action_verified': False, 'read_only': True}
    state = saved.get('state', 'unknown')
    readable = kind.replace('_', ' ')
    result = {'action_verified': True, 'read_only': True, 'action': {'kind': kind, 'proposal_id': pid,
              'state': state, 'executed': saved.get('executed') is True}, 'workspace': current}
    if state == 'executed' and saved.get('executed') is True and not saved.get('requires_manual_review'):
        result['answer'] = f'The saved {readable} action is confirmed executed. This confirms the internal action, not customer delivery or payment.'
        if saved.get('current_record_matches') is False:
            result['answer'] += ' The underlying record has changed since this action; check its current state before proceeding.'
        if current == 'doorks' and kind in ('new_work_order', 'estimate_draft'):
            from app.services.moses_butler_flow import next_step
            try:
                following = next_step(request, kind, pid)
            except HTTPException:
                following = None
            if isinstance(following, dict) and following.get('available') is True:
                next_kind = following.get('next_kind')
                next_target = following.get('record_id')
                if next_kind in ('estimate_draft', 'estimate_to_invoice') and isinstance(next_target, str) and next_target:
                    result['next_action'] = {'kind': next_kind, 'record_id': next_target,
                                             'approval_required': True}
                    result['answer'] += (' The next available step is an unpriced estimate draft.'
                                         if next_kind == 'estimate_draft' else
                                         ' The next available step is a draft invoice proposal.')
            elif isinstance(following, dict) and following.get('reason'):
                result['answer'] += ' Next step is not currently eligible: ' + str(following['reason'])[:180]
        return result
    if state == 'pending':
        result['answer'] = f'The {readable} action is waiting for office approval. No execution is confirmed.'
    elif state == 'rejected':
        result['answer'] = f'The {readable} action was rejected. It was not executed.'
    elif state in ('executing', 'uncertain', 'needs_review') or saved.get('requires_manual_review'):
        result['answer'] = f'The {readable} action requires manual review ({state}). Do not approve or retry it blindly.'
    else:
        result['answer'] = f'I found the {readable} action, but its state ({state}) does not confirm execution.'
    return result
