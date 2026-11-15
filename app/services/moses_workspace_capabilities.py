"""Conservative workspace capability reporting for release validation.

This is a description of integrated Moses tools, not a claim of UI/editor parity.
It never reads business records or modifies data. Feature availability remains
subject to each business action's existing server-side authorization checks.
"""
from __future__ import annotations

import os
from fastapi import HTTPException

READ_ONLY = {
    'doorks': ('workspace_record_search', 'work_order_lookup', 'purchase_order_receiving_review',
               'supplier_bill_match', 'supplier_payment_reconciliation', 'stripe_test_status'),
    'pds': ('pds_job_lookup', 'pds_job_detail', 'purchase_order_receiving_review'),
    'sdc': ('workspace_record_search', 'order_status_reporting', 'expense_reporting',
            'purchase_order_receiving_review', 'stripe_test_status'),
}
PROPOSALS = {
    'doorks': ('work_order', 'status', 'schedule', 'estimate_draft', 'draft_invoice',
               'purchase_order', 'receiving', 'supplier_bill', 'part', 'email_preview',
               'invoice_test_checkout'),
    'pds': ('job_status', 'receiving', 'part', 'email_preview'),
    'sdc': ('order_status', 'draft_invoice', 'purchase_order', 'receiving', 'part',
            'email_preview', 'invoice_test_checkout'),
}
# These are known non-parity areas: do not report shared editor access as complete.
UNVERIFIED = (
    'same_ticket_editor_across_office_customer_vendor',
    'same_estimate_invoice_editor_across_all_workspaces',
    'pds_sdc_doorks_accounting_hub_full_parity',
    'live_agents_sdk_execution',
    'live_resend_delivery',
    'live_stripe_sandbox_transaction',
    'authenticated_browser_end_to_end',
    'off_server_production_backup_restore',
)
FLAGS = {
    'doorks': 'DOORKS_MOSES_DOORKS_AGENT_ENABLED',
    'pds': 'DOORKS_MOSES_PDS_AGENT_ENABLED',
    'sdc': 'DOORKS_SDC_AGENT_ENABLED',
}


def inspect(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in to use Moses')
    platform = request.session.get('active_platform')
    if platform not in FLAGS or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Workspace office-admin access required')
    return {
        'workspace': platform,
        'agent_enabled': os.getenv(FLAGS[platform], '').strip().lower() == 'true',
        'read_only_tools': list(READ_ONLY[platform]),
        'approval_proposal_categories': list(PROPOSALS[platform]),
        'full_editor_parity_verified': False,
        'release_checks_outstanding': list(UNVERIFIED),
        'note': ('Capability inventory is a code-level contract, not evidence of live execution. '
                 'Each proposal requires its existing feature gate and authorization; '
                 'external sending and payments are not implied.'),
    }
