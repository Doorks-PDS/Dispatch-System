"""Rev 75 safety/contract checks for customer and vendor portal changes."""
from pathlib import Path
from pydantic import ValidationError
from app.routers.doorks_portals import CustomerWorkOrderChange

def test_customer_change_requires_note():
    try:
        CustomerWorkOrderChange(work_order_id='a',note='x')
        assert False, 'Too-short notes must fail'
    except ValidationError:
        pass

def test_change_request_cannot_claim_arbitrary_role():
    p=CustomerWorkOrderChange(work_order_id='wo1',note='Please move to Friday',request_type='schedule_change')
    assert p.request_type=='schedule_change'
    assert not hasattr(p,'customer_id')

def test_calendar_and_checkout_present():
    html=(Path(__file__).resolve().parents[1]/'static/doorks_home.html').read_text()
    assert 'portalCalendar(v,work,portalJobDetails)' in html
    assert "accounts/work-orders/change-request" in html
    assert 'accounts/checkout' in html
