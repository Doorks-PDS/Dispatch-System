from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_office_decision_requires_admin_and_pending_request():
    code=(ROOT/'app/routers/doorks_portals.py').read_text()
    body=code.split('def decide_operational_change(',1)[1].split('class SubmissionQueueAction',1)[0]
    assert 'admin(request)' in body
    assert "item.get('status') != 'pending_review'" in body
    assert "'customer_work_order_change'" in body
    assert "'vendor_assignment_change_request'" in body
    assert 'write(path, data)' in body

def test_approval_does_not_silently_mutate_dispatch():
    code=(ROOT/'app/routers/doorks_portals.py').read_text()
    body=code.split('def decide_operational_change(',1)[1].split('class SubmissionQueueAction',1)[0]
    assert "'approved_pending_application'" in body
    assert 'applied_to_source=False' in body
    assert "'applied_to_source': False" in body
    assert 'review_history' in body
