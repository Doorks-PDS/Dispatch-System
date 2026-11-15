"""Read-only, verified customer payment receipt preview. No sending/accounting posting.

The old customer portal and the Moses workspace checkout have distinct ledgers;
this module intentionally reads ONLY the workspace checkout ledger.
"""
from __future__ import annotations
from fastapi import HTTPException
from app.services import moses_stripe as stripe


def preview(request, platform: str, record_id: str):
    """Prepare a safe confirmation draft only for one verified, unchanged paid checkout."""
    stripe._admin(request, platform)
    status = stripe.payment_status(request, platform, record_id)
    if status['stripe_payment_requires_review']:
        raise HTTPException(409, 'Payment requires reconciliation review')
    matching = [r for r in status['checkouts']
                if r['stripe_payment_confirmed'] and r['matches_current_invoice']]
    if len(matching) != 1:
        raise HTTPException(409, 'Exactly one matching Stripe payment is required')
    snapshot = stripe._snapshot(request, platform, record_id)
    if snapshot['amount_cents'] != matching[0]['amount_cents']:
        raise HTTPException(409, 'Payment amount changed')
    # Do not disclose the checkout bearer URL or customer personal data beyond
    # the authorized recipient of the specific invoice.
    dollars = f"{snapshot['amount_cents'] / 100:,.2f}"
    return {
        'platform': platform, 'record_id': record_id,
        'invoice_number': snapshot['number'], 'to': snapshot['recipient'],
        'recipient_source': snapshot['recipient_source'],
        'subject': f"Payment confirmation for invoice {snapshot['number']}",
        'message': (f"We have received a Stripe payment of ${dollars} "
                    f"for invoice {snapshot['number']}. Thank you.\n\n"
                    "Please contact our accounting team with any questions."),
        'stripe_payment_confirmed': True,
        'accounting_reconciled': False,
        'send_enabled': False,
        'note': 'Preview only. No email sent; no accounting entry or invoice status updated.',
    }
