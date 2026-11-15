"""Read-only, conservative readiness assessment for a controlled Moses rollout.

No external requests, disk writes, secrets, or irreversible actions. A successful
local check cannot establish Render disk durability or provider connectivity.
"""
from __future__ import annotations

import os

from app.services.moses_agent import readiness as agent_readiness
from app.services.moses_storage_readiness import inspect as storage_inspect

WORKSPACES = ('pds', 'doorks', 'sdc')
# These are opt-in, externally consequential Moses capabilities; reported only
# as boolean configuration observations, never as proof of actual execution.
ACTION_FLAGS = (
    'DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED',
    'DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED',
    'DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED',
    'DOORKS_SDC_MOSES_ACTIONS_ENABLED',
    'MOSES_DISPATCH_SEND_ENABLED',
    'MOSES_ESTIMATE_SEND_ENABLED',
    'MOSES_INVOICE_SEND_ENABLED',
    'MOSES_PO_SEND_ENABLED',
    'MOSES_RECEIVING_ACTIONS_ENABLED',
    'MOSES_SUPPLIER_BILL_ACTIONS_ENABLED',
    'MOSES_STRIPE_TEST_ENABLED',
)


def assess(data_dir: str) -> dict:
    """Return explicit local preflight facts, never a fabricated production pass."""
    storage = storage_inspect(data_dir, expected_disk_mount=os.getenv('MOSES_EXPECTED_RENDER_DISK_MOUNT') or None)
    agents = {space: agent_readiness(space) for space in WORKSPACES}
    provider = os.getenv('MOSES_EMAIL_PROVIDER', 'smtp').strip().lower()
    email_configured = (bool(os.getenv('RESEND_API_KEY', '').startswith('re_'))
                        and bool(os.getenv('MOSES_DOCUMENTS_FROM', '').strip())) if provider == 'resend' else False
    stripe_enabled = os.getenv('MOSES_STRIPE_TEST_ENABLED', '').strip().lower() == 'true'
    stripe_test_key = os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_')
    webhook_configured = os.getenv('RESEND_WEBHOOK_SECRET', '').startswith('whsec_')
    enabled_actions = [key for key in ACTION_FLAGS if os.getenv(key, '').strip().lower() == 'true']
    return {
        'deployment_authorized': False,
        'production_end_to_end_verified': False,
        'storage': storage,
        'agents': agents,
        'email': {
            'provider': provider,
            'resend_key_configured': email_configured,
            'resend_webhook_secret_configured': webhook_configured,
            'live_delivery_verified': False,
        },
        'payments': {
            'test_mode_enabled': stripe_enabled,
            'test_key_configured': stripe_test_key,
            'sandbox_payment_verified': False,
        },
        'disk_mount_alignment_required': storage['configured_path_under_expected_disk'] is not True,
        'enabled_external_or_write_actions': enabled_actions,
        'actions_fully_disabled': not enabled_actions,
        'release_blockers': [
            'Confirm production Render durable storage and recoverable backup.',
            'Verify authenticated live agent conversation, approval, and saved action.',
            'Verify Resend test email and signed delivery event.',
            'Verify Stripe sandbox checkout and signed webhook separately from legacy portal.',
            'Verify office and field browser smoke tests in PDS, Doorks, and SDC.',
        ],
        'note': 'Read-only configuration observations are not proof of live behavior. No secret values are returned.',
    }
