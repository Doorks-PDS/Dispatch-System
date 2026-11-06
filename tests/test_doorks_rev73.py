from app.routers import doorks_portals as p
from pydantic import ValidationError

def test_vendor_commercial_routes_registered():
    paths={r.path for r in p.router.routes}
    for path in ('/doorks-portals/vendor-account/commercial-documents',
                 '/doorks-portals/admin/vendor-commercial-documents',
                 '/doorks-portals/admin/vendor-commercial-documents/{document_id}/review',
                 '/doorks-portals/vendor-account/assignments/messages',
                 '/doorks-portals/admin/vendor-assignments/{assignment_id}/messages'):
        assert path in paths

def test_vendor_document_requires_nonnegative_amount_and_description():
    try:
        p.VendorCommercialDocument(assignment_id='a',document_type='invoice',description='',amount=-1)
    except ValidationError:
        pass
    else:
        assert False

def test_vendor_review_is_explicit():
    try:
        p.VendorDocumentReview(decision='paid')
    except ValidationError:
        pass
    else:
        assert False
