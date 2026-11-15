"""Office-admin-scoped Moses capability visibility, without enabling any operation.

Reports what is configured for the active workspace. These checks are NOT
execution authorization, live delivery verification, or substitute approval.
Every individual execution handler retains its own role, record, confirmation,
and provider checks. No business records are read or written here.
"""
from __future__ import annotations

import os
from fastapi import HTTPException

# Verified against the existing action-guard environment variables. Each
# capability maps to its specific implementation, not generic superuser access.
CAPABILITIES = {
    'pds': (
        ('jobs', 'Search jobs, completion forms and prepare unpriced estimates', None),
        ('status', 'Propose a PDS work-order status update', 'DOORKS_MOSES_PDS_STATUS_ACTIONS_ENABLED'),
        ('parts', 'Propose PDS catalog parts', 'DOORKS_MOSES_PDS_PART_ACTIONS_ENABLED'),
        ('dispatch_email', 'Propose approved customer dispatch email', 'MOSES_DISPATCH_SEND_ENABLED'),
        ('purchase_order_email', 'Propose approved vendor PO email', 'MOSES_PO_SEND_ENABLED'),
    ),
    'doorks': (
        ('records', 'Search jobs, customers, vendors and documents', None),
        ('operations', 'Propose work orders, scheduling and status changes', 'DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED'),
        ('purchasing', 'Propose draft purchase orders', 'DOORKS_MOSES_WORK_ORDER_ACTIONS_ENABLED'),
        ('receiving', 'Propose PO receipts', 'MOSES_RECEIVING_ACTIONS_ENABLED'),
        ('supplier_bills', 'Propose supplier bills for approval', 'MOSES_SUPPLIER_BILL_ACTIONS_ENABLED'),
        ('dispatch_email', 'Propose approved customer dispatch email', 'MOSES_DISPATCH_SEND_ENABLED'),
        ('estimate_email', 'Propose approved estimate delivery', 'MOSES_ESTIMATE_SEND_ENABLED'),
        ('invoice_email', 'Propose approved invoice delivery', 'MOSES_INVOICE_SEND_ENABLED'),
        ('purchase_order_email', 'Propose approved vendor PO email', 'MOSES_PO_SEND_ENABLED'),
        ('stripe_test', 'Propose test-mode Stripe Checkout', 'MOSES_STRIPE_TEST_ENABLED'),
    ),
    'sdc': (
        ('records', 'Search orders, leads, customers, vendors and documents', None),
        ('operations', 'Propose order-status changes', 'DOORKS_SDC_MOSES_ACTIONS_ENABLED'),
        ('purchasing', 'Propose draft purchase orders', 'DOORKS_SDC_MOSES_ACTIONS_ENABLED'),
        ('receiving', 'Propose PO receipts', 'MOSES_RECEIVING_ACTIONS_ENABLED'),
        ('supplier_bills', 'Propose supplier bills for approval', 'MOSES_SUPPLIER_BILL_ACTIONS_ENABLED'),
        ('estimate_email', 'Propose approved estimate delivery', 'MOSES_ESTIMATE_SEND_ENABLED'),
        ('invoice_email', 'Propose approved invoice delivery', 'MOSES_INVOICE_SEND_ENABLED'),
        ('purchase_order_email', 'Propose approved vendor PO email', 'MOSES_PO_SEND_ENABLED'),
        ('stripe_test', 'Propose test-mode Stripe Checkout', 'MOSES_STRIPE_TEST_ENABLED'),
    ),
}
AGENT_FLAGS = {
    'pds': 'DOORKS_MOSES_PDS_AGENT_ENABLED',
    'doorks': 'DOORKS_MOSES_DOORKS_AGENT_ENABLED',
    'sdc': 'DOORKS_SDC_AGENT_ENABLED',
}


def _enabled(flag: str | None) -> bool:
    return flag is None or os.getenv(flag, '').strip().lower() == 'true'


def _guard(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Sign in to use Moses')
    workspace = request.session.get('active_platform')
    if workspace not in CAPABILITIES or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active workspace office-admin access required')
    return workspace


def _email_prerequisites():
    """Configuration hints only; never attempt a send or return a secret."""
    provider = os.getenv('MOSES_EMAIL_PROVIDER', 'smtp').strip().lower()
    if provider == 'resend':
        return (bool(os.getenv('RESEND_API_KEY', '').startswith('re_'))
                and bool(os.getenv('MOSES_DOCUMENTS_FROM', '').strip()))
    if provider == 'smtp':
        required = ('DOORKS_SMTP_HOST', 'DOORKS_SMTP_USERNAME',
                    'DOORKS_SMTP_PASSWORD', 'DOORKS_SMTP_FROM')
        return all(bool(os.getenv(key, '').strip()) for key in required)
    return False


def inspect(request):
    """Return capability states, never credentials or business records."""
    workspace = _guard(request)
    out = []
    for ident, description, flag in CAPABILITIES[workspace]:
        configured = _enabled(flag)
        provider_configured = True
        if ident.endswith('_email'):
            provider_configured = _email_prerequisites()
        elif ident == 'stripe_test':
            provider_configured = os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_')
        state = ('read_only' if flag is None else
                 'disabled' if not configured else
                 'provider_setup_required' if not provider_configured else
                 'proposal_enabled')
        out.append({'id': ident, 'description': description,
                    'status': state, 'approval_required': flag is not None,
                    'configured': configured,
                    'provider_configured': provider_configured,
                    'execution_verified': False})
    return out


def report(request):
    workspace = _guard(request)
    capabilities = inspect(request)
    agent_flag = AGENT_FLAGS[workspace]
    agent_configured = _enabled(agent_flag)
    missing = sorted({flag for _, _, flag in CAPABILITIES[workspace]
                      if flag and not _enabled(flag)})
    if not agent_configured:
        missing.insert(0, agent_flag)
    provider_blockers = [item['id'] for item in capabilities
                         if item['status'] == 'provider_setup_required']
    return {
        'workspace': workspace,
        'agent_enabled': agent_configured,
        'capabilities': capabilities,
        'missing_configuration_flags': missing,
        'provider_setup_required': provider_blockers,
        'all_configured': not missing and not provider_blockers,
        'all_live_actions_verified': False,
        'approval_policy': 'Per-action explicit office-admin review; never direct execution from the model',
        'notes': ('Configured does not mean provider-connected, approved, or live-verified. '
                  'Stripe remains TEST MODE ONLY. PDS accounting and employee payroll updates '
                  'are not authorized by these permissions.'),
    }
