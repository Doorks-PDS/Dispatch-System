"""Manual, isolated OpenAI Agents SDK tool-call validation for a Moses workspace.

This test never loads customer records, writes to a workspace, or executes business
approvals. A passing result proves one synthetic model/tool round trip only.
"""
from __future__ import annotations

import os
import re
import uuid


def check(workspace: str) -> dict:
    from app.services.moses_agent import readiness

    result = {
        'workspace': workspace,
        'live_api_verified': False,
        'sdk_tool_execution_verified': False,
        'record_access_verified': False,
        'approval_execution_verified': False,
        'production_end_to_end_verified': False,
        'deployment_authorized': False,
    }
    try:
        state = readiness(workspace)
    except (ValueError, RuntimeError, ImportError):
        return {**result, 'result': 'invalid_workspace_or_configuration'}
    if not state.get('ready_for_live_check'):
        return {**result, 'result': 'not_configured'}
    # This is an explicit, cost-incurring test, never run on service startup.
    # Workspace flags alone do not authorize live provider calls.
    if os.getenv('MOSES_LIVE_VALIDATION_ENABLED', '').strip().lower() != 'true':
        return {**result, 'result': 'live_test_not_enabled'}

    model = os.getenv('DOORKS_MOSES_MODEL', 'gpt-4.1-mini')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,99}', model):
        return {**result, 'result': 'invalid_model'}

    try:
        from agents import Agent, Runner, RunConfig, function_tool
        challenge = uuid.uuid4().hex
        called = []

        @function_tool
        def synthetic_ping(challenge_token: str) -> str:
            """Return a marker for the exact synthetic challenge token provided.

            Args:
                challenge_token: The token explicitly supplied in the test prompt.
            """
            if challenge_token != challenge:
                return 'INCORRECT_CHALLENGE'
            called.append(True)
            return 'MOSES_SYNTHETIC_TOOL_OK'

        agent = Agent(
            name='Moses isolated SDK verification',
            model=model,
            instructions=(
                'This is a synthetic service health check with no business data. '
                'Call synthetic_ping with the exact challenge token in the user message. '
                'After the tool returns, briefly acknowledge success. '
                'Do not use or invent customer records.'
            ),
            tools=[synthetic_ping],
        )
        run = Runner.run_sync(
            agent,
            [{'role': 'user', 'content': 'Call synthetic_ping using challenge_token=' + challenge}],
            max_turns=3,
            run_config=RunConfig(tracing_disabled=True),
        )
        verified = bool(called) and bool(str(getattr(run, 'final_output', '') or '').strip())
        return {**result, 'live_api_verified': verified,
                'sdk_tool_execution_verified': verified,
                'result': 'synthetic_tool_verified' if verified else 'tool_not_verified'}
    except Exception:
        # Do not leak provider errors, credentials, or model traces to the client.
        return {**result, 'result': 'provider_or_sdk_call_failed'}
