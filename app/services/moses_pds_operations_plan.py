"""Conservative PDS operations board using the saved work and review stores."""
from __future__ import annotations
from app.services import moses_pds_invoice_plan
from app.services.moses_pds_quote_triage import triage


def board(request):
    moses_pds_invoice_plan._guard(request)
    quote=triage(request,limit=20)
    invoices=moses_pds_invoice_plan.receipts(request)
    return {'workspace':'pds','read_only':True,
            'quote_needing_attention':quote['counts'],
            'invoice_review_packets':invoices['receipts'],
            'note':'Source-backed readiness and saved review packets; no estimates or invoices issued.'}


def receipts(request):
    return moses_pds_invoice_plan.receipts(request)
