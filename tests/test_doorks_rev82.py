from pathlib import Path

def test_compliance_expiration_report_is_admin_scoped():
    source=Path('app/routers/doorks_portals.py').read_text()
    start=source.index("@router.get('/admin/vendor-compliance/expiring')")
    endpoint=source[start:]
    assert 'admin(request)' in endpoint
    assert "entry.get('status') != 'approved'" in endpoint
    assert "entry.get('source_record_type') != 'vendor_profile'" in endpoint
    assert "'days_remaining':remaining" in endpoint


def test_vendor_print_preview_is_not_posted_invoice():
    source=Path('static/doorks_home.html').read_text()
    assert 'Preview / Print branded document' in source
    assert 'Not a posted customer invoice or approved estimate.' in source
    assert 'Moses — Read attached document' in source
