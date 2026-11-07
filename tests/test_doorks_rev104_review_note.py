"""Review decisions must be auditable; no silent dispatch mutation."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_rejection_and_clarification_require_explanation():
    src = (ROOT / 'app/routers/doorks_portals.py').read_text()
    body = src.split('def decide_operational_change(', 1)[1].split('class OperationalChangeApplied', 1)[0]
    assert "payload.decision in ('reject', 'request_clarification')" in body
    assert 'not payload.note.strip()' in body
    assert "HTTPException(422, 'A review note is required" in body
    assert "'approved_pending_application'" in body
    assert 'applied_to_source=False' in body
