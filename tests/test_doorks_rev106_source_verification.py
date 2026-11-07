"""Operational requests must not be marked applied without a source change."""
from pathlib import Path
import importlib.util

def test_source_fingerprint_changes_when_record_changes():
    from app.routers.doorks_portals import _operational_source_fingerprint as fingerprint
    original={"id":"abc","status":"Scheduled","address":"A"}
    assert fingerprint(original)==fingerprint(dict(original))
    assert fingerprint(original)!=fingerprint({**original,"status":"In Progress"})

def test_request_captures_source_snapshot_and_confirm_checks_it():
    text=(Path(__file__).resolve().parents[1]/"app/routers/doorks_portals.py").read_text()
    assert text.count("'source_fingerprint_at_request':_operational_source_fingerprint(")==2
    assert "if saved_fingerprint == original_fingerprint:" in text
    assert "source_fingerprint_at_application=saved_fingerprint" in text
