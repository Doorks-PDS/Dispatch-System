from app.routers import doorks_portals as p
from pydantic import ValidationError

def test_registration_requires_role_and_confirmations():
    try: p.PortalRegistration(email='test@example.com',contact_name='Test Person',company='Example',password='long-password-123')
    except ValidationError: pass
    else: assert False

def test_password_reset_routes_present():
    paths={r.path for r in p.router.routes}
    assert '/doorks-portals/accounts/forgot-password' in paths
    assert '/doorks-portals/accounts/reset-password' in paths
    assert '/doorks-portals/admin/accounts/{account_id}/password-reset-link' in paths

def test_registration_rejects_mismatched_passwords():
    assert p.PortalRegistration(email='test@example.com',contact_name='Test Person',company='Example',password='long-password-123',password_confirm='different-pass-123',role='vendor',role_confirm='vendor').password != 'different-pass-123'
