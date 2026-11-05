from datetime import date
from decimal import Decimal
from app.routers.doorks_operations import effective_rate,card_rate,card_gross
from app.routers.doorks_portals import Invite,PortalRegistration,PortalApproval

def test_effective_dated_rates_not_retroactive():
    e={'hourly_rate':'30','wage_history':[{'effective_date':'2026-11-01','hourly_rate':'30'},{'effective_date':'2026-11-15','hourly_rate':'31'}]}
    assert effective_rate(e,'2026-11-10')==Decimal('30.00')
    assert effective_rate(e,'2026-11-20')==Decimal('31.00')
    assert effective_rate(e,'2026-10-15') is None

def test_approved_snapshot_immutable_after_raise():
    card={'work_date':'2026-11-10','hourly_rate_snapshot':30,'regular_hours':8,'overtime_hours':2}
    e={'hourly_rate':'50','wage_history':[{'effective_date':'2026-11-15','hourly_rate':'50'}]}
    assert card_rate(card,e)==Decimal('30.00')
    assert card_gross(card,card_rate(card,e))==Decimal('330.00')

def test_permanent_vendor_invitation_and_account_role():
    assert Invite(kind='vendor',contact_name='A',contact_email='a@example.com',company='V',days=0).days==0
    assert PortalRegistration(email='v@example.com',contact_name='Vendor',company='V',password='123456789012',role='vendor').role=='vendor'
    assert PortalApproval(vendor_id='vendor-id').vendor_id=='vendor-id'
