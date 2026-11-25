"""Manually verify hosted public web search for the configured Moses agent.

No saved records, business context, user data, or messages leave this function.
A model response alone cannot certify search: a real web_search_call must appear
in the API response. Only an authorized office admin can invoke the HTTP route.
"""
from __future__ import annotations

import os


def _web_search_called(result) -> bool:
    """Inspect raw hosted-tool call evidence, not model-written assertions."""
    for response in getattr(result, 'raw_responses', ()) or ():
        for item in getattr(response, 'output', ()) or ():
            kind = item.get('type') if isinstance(item, dict) else getattr(item, 'type', '')
            if kind == 'web_search_call':
                status = item.get('status') if isinstance(item, dict) else getattr(item, 'status', None)
                # A failed hosted call is not evidence of a usable web connection.
                if status not in ('failed', 'in_progress', 'searching'):
                    return True
    return False


def check(workspace: str) -> dict:
    from app.services.moses_agent import readiness
    result = {'workspace': workspace, 'web_search_verified': False,
              'business_record_access_verified': False, 'business_actions_verified': False,
              'customer_data_used': False, 'outbound_messages_sent': False}
    try:
        state = readiness(workspace)
    except (ValueError, RuntimeError, ImportError):
        return {**result, 'result': 'invalid_workspace_or_configuration'}
    if not state.get('ready_for_live_check'):
        return {**result, 'result': 'agent_not_configured'}
    if not state.get('internet_research_requested'):
        return {**result, 'result': 'web_search_disabled'}
    if not state.get('web_live_test_enabled'):
        return {**result, 'result': 'live_test_not_enabled'}
    try:
        from agents import Agent, Runner, RunConfig, WebSearchTool
        model = os.getenv('DOORKS_MOSES_MODEL', 'gpt-4.1-mini')
        agent = Agent(name='Moses public web-search verification', model=model,
                      instructions=('Use the hosted web search tool to find the official OpenAI '
                                    'documentation for web search. This is a synthetic diagnostic. '
                                    'Do not request, read or mention private business records. '
                                    'Do not use any business tools. Summarize the official page briefly.'),
                      tools=[WebSearchTool(search_context_size='low')])
        run = Runner.run_sync(agent,
                              [{'role': 'user', 'content':
                                'Search the public web for the official OpenAI API web search documentation.'}],
                              max_turns=3, run_config=RunConfig(tracing_disabled=True))
        called = _web_search_called(run)
        answered = bool(str(getattr(run, 'final_output', '') or '').strip())
        verified = called and answered
        return {**result, 'web_search_verified': verified,
                'result': 'hosted_web_search_verified' if verified else 'no_confirmed_web_call'}
    except Exception as exc:
        # Only safe diagnostic categories: never reveal provider response bodies,
        # credentials, private data, or arbitrary exception messages to the UI.
        error_kind = type(exc).__name__
        reasons = {
            'AuthenticationError': 'api_key_rejected',
            'PermissionDeniedError': 'api_project_permission_denied',
            'RateLimitError': 'api_quota_or_rate_limit',
            'BadRequestError': 'model_or_hosted_web_tool_rejected',
            'APITimeoutError': 'provider_timeout',
            'APIConnectionError': 'provider_network_unavailable',
            'MaxTurnsExceeded': 'web_search_did_not_finish',
        }
        return {**result, 'result': reasons.get(error_kind, 'web_provider_or_sdk_check_failed')}
