"""Read-only PDS invoice fee/payment plan (Rev 5.72).

No invoice, customer, payout, fee or payment is created/changed. Actual
collection and SDC revenue sharing require an explicitly approved compliant
invoice-line policy and a verified payment processor/accounting integration.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from app.services import pds_quickbooks_bridge as qb

RATE = Decimal('0')  # Universal service fee proposal withdrawn; no charge
CENT = Decimal('0.01')
ALL_METHODS = ('credit_card', 'debit_card', 'ach_echeck', 'check', 'cash', 'other')


def summary(request):
    qb._admin(request)
    return {
        'service_fee_name': 'Service fee (withdrawn)', 'rate_percent': '0.00',
        'applies_to': list(ALL_METHODS), 'base': 'pre_tax_invoice_subtotal',
        'application_state': 'withdrawn_not_charged',
        'enabled_for_new_invoices': False,
        'applied_to_existing_invoices': False,
        'fee_shown_on_issued_pdf': False,
        'stripe_connect_enabled': False, 'quickbooks_payment_sync_enabled': False,
        'sdc_collection_verified': False,
        'payment_link_status': 'not_connected',
        'tax_treatment': 'needs_accountant_review',
        'accounting': {
            'merchant_of_record': 'pds_proposed',
            'service_fee_revenue_owner': 'none',
            'requires_separate_fee_line': False,
            'requires_income_liability_mapping': False,
            'requires_processor_reconciliation': True,
        },
        'note': 'Universal service fee proposal withdrawn. No fee is added to invoices or payments.',
    }


def invoice_preview(request, invoice_number):
    qb._admin(request)
    if not qb.INVOICE_RE.fullmatch(str(invoice_number or '')):
        raise HTTPException(422, 'Use an exact PDS invoice number')
    record = qb._rows(request).get(invoice_number.upper())
    if not record:
        raise HTTPException(404, 'Saved PDS invoice not found')
    if record['needs_review']:
        return {'number': record['number'], 'ready': False,
                'needs_review': record['needs_review'], 'fee_charged': False,
                'payment_link_available': False}
    base = Decimal(record['subtotal'])
    fee = (base * RATE).quantize(CENT, rounding=ROUND_HALF_UP)
    existing_total = Decimal(record['total'])
    # This is *not* a billable total. Tax treatment (and whether the customer
    # has agreed to the full amount) must be settled before adding a line.
    return {'number': record['number'], 'ready': True,
            'existing_invoice_total': f'{existing_total:.2f}',
            'base_pre_tax_subtotal': f'{base:.2f}',
            'proposed_service_fee': f'{fee:.2f}',
            'illustrative_total_before_any_fee_tax': f'{(existing_total + fee):.2f}',
            'fee_charged': False, 'fee_applied_to_document': False,
            'payment_link_available': False,
            'all_payment_methods': list(ALL_METHODS),
            'note': 'No added service fee. The saved customer invoice and QuickBooks handoff are unchanged.'}
