"""Manual, read-only Moses provider verification.

NO customer records, emails, payment sessions, or mutations. This is NOT a
substitute for a test send or a signed webhook round trip. Called only from a
logged-in office-admin route; never from import, startup or a scheduler.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen

from fastapi import HTTPException


def _require_admin(request):
    if not getattr(request.state, 'auth_user', None):
        raise HTTPException(401, 'Login required')
    platform = request.session.get('active_platform')
    if platform not in ('pds', 'doorks', 'sdc') or getattr(request.state, 'auth_role', None) != 'office_admin':
        raise HTTPException(403, 'Active office-admin workspace required')
    return platform


def _json_get(url: str, key: str, *, limit=32768) -> dict:
    """Return bounded provider JSON; never return or log keys or error bodies."""
    request = URLRequest(url, method='GET', headers={'Authorization': 'Bearer ' + key,
                        'Accept': 'application/json', 'User-Agent': 'Moses-Provider-Readiness/1.0'})
    with urlopen(request, timeout=7) as response:
        if response.status != 200:
            raise ValueError('provider_not_ok')
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('provider_response_too_large')
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise ValueError('provider_response_invalid')
        return parsed


def inspect(request):
    """Probe Resend sending domain and Stripe *test* account using GET only.

    Never includes provider-supplied names, arbitrary error text, secret values,
    customer information or external IDs in the response. No customer emails
    or Stripe sessions are created.
    """
    platform = _require_admin(request)
    from app.services.moses_mail_identity import identity
    sender = identity(platform, 'estimate')
    address = sender.get('from') or ''
    domain = address.rsplit('@', 1)[-1].casefold() if '@' in address else ''
    result = {
        'workspace': platform,
        'read_only': True,
        'customer_email_sent': False,
        'checkout_created': False,
        'webhook_roundtrip_verified': False,
        'ai_sdk_tool_verified': False,
        'resend': {'configured': False, 'sender_domain_verified': False,
                   'result': 'not_configured'},
        'stripe': {'test_key_configured': False, 'account_verified': False,
                   'expected_account_matched': False, 'result': 'not_configured'},
    }
    resend_key = os.getenv('RESEND_API_KEY', '')
    if os.getenv('MOSES_EMAIL_PROVIDER', '').strip().lower() == 'resend' and resend_key.startswith('re_') and domain:
        result['resend']['configured'] = True
        try:
            data = _json_get('https://api.resend.com/domains', resend_key)
            domains = data.get('data')
            if not isinstance(domains, list):
                raise ValueError('unexpected_response')
            matched = [row for row in domains if isinstance(row, dict)
                       and str(row.get('name') or '').casefold() == domain]
            verified = any(row.get('status') == 'verified' for row in matched)
            result['resend'].update(sender_domain_verified=verified,
                                    result='domain_verified' if verified else 'sender_domain_not_verified')
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            result['resend']['result'] = 'provider_check_failed'
    secret = os.getenv('STRIPE_SECRET_KEY', '')
    if os.getenv('MOSES_STRIPE_TEST_ENABLED', '').lower().strip() == 'true' and secret.startswith('sk_test_'):
        result['stripe']['test_key_configured'] = True
        try:
            account = _json_get('https://api.stripe.com/v1/account', secret)
            actual = str(account.get('id') or '')
            expected = os.getenv('MOSES_STRIPE_EXPECTED_ACCOUNT_ID', '').strip()
            verified = actual.startswith('acct_') and account.get('object') == 'account'
            matched = bool(expected and verified and actual == expected)
            result['stripe'].update(account_verified=verified,
                                    expected_account_matched=matched,
                                    result=('expected_sandbox_account_verified' if matched
                                            else 'expected_account_not_configured' if verified and not expected
                                            else 'sandbox_account_mismatch' if verified
                                            else 'invalid_account_response'))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            result['stripe']['result'] = 'provider_check_failed'
    return result
