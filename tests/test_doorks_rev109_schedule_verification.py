import pytest
from fastapi import HTTPException
from app.routers.doorks_portals import _operational_schedule_evidence as check

def test_schedule_requires_exact_saved_fields_and_changed_snapshot():
    item={'kind':'customer_work_order_change','request_type':'schedule_change',
          'preferred_date':'2026-11-20','preferred_time':'13:30',
          'source_schedule_at_request':{'scheduled_date':'2026-11-19','scheduled_time':'09:00'}}
    result=check(item,{'scheduled_date':'2026-11-20','scheduled_time':'13:30'})
    assert result['verification']=='schedule_fields_matched'
    for source in ({'scheduled_date':'2026-11-19','scheduled_time':'13:30'},
                   {'scheduled_date':'2026-11-20','scheduled_time':'09:00'}):
        with pytest.raises(HTTPException): check(item,source)

def test_unstructured_and_legacy_schedule_requests_fail_closed():
    item={'kind':'vendor_assignment_change_request','change_type':'schedule',
          'proposed_date':'2026-11-20','source_schedule_at_request':{'scheduled_date':'2026-11-19'}}
    with pytest.raises(HTTPException): check(item,{'scheduled_date':'2026-11-21'})
    with pytest.raises(HTTPException): check({**item,'source_schedule_at_request':None},{'scheduled_date':'2026-11-20'})
    assert check({'kind':'vendor_assignment_change_request','change_type':'scope'}, {})['verification']=='source_changed_office_attested'
