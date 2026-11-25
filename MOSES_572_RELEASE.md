# Moses 5.72 — recipient lists, QuickBooks sync previews, service-fee planning

Built against committed Doorks 5.71 on `main` (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`).

## Changes

- Saved PDS estimate/invoice Resend composer: separate semicolon/comma-separated To and CC fields, verified customer-contact suggestions from exact-company CRM matches, saved approvals include the complete recipient list.
- Technician email approvals: technicians may select only saved customer contact addresses. Office reviews the exact recipients and attached saved PDF prior to approval and send. Office may explicitly enter extra valid addresses. No unsupervised sending.
- Resend transport: supports one or multiple To/CC recipients, exact email validation, length and count bounds, deduplication, and existing idempotency / uncertain-send safeguards. An already-accepted document cannot silently be resent to a new recipient. Provider acceptance is **not** inbox delivery.
- QuickBooks Invoice/PO **read-only sync payload previews**: preserve the original JS/PO number, job number, customer/vendor, line items, tax/total, staged fingerprint and numbering policy. They are not ready for posting until the QuickBooks company, item/tax/customer/vendor mappings and authorization are validated.
- Invoice stage fingerprint now includes the full source metadata, not just summary amounts. Same-price description edits and duplicate local invoice numbers fail closed.
- QuickBooks Hub > Payments & fees: universal **0.5% service-fee plan**, displayed separately and calculated from pre-tax subtotal for review. This does not change existing documents, quote prices, customer charges, or payment totals. Fee tax treatment and contract pricing disclosure need approval before activation.

## Safety/finance boundary

- **No live QuickBooks API or OAuth token connection**, no QuickBooks invoice or PO creation, no payment posting.
- **No live payment links, Stripe Connect transfers or fees** created. Separating PDS revenue from a proposed SDC fee will require a real payment or intercompany accounting flow; a printed label alone cannot transfer money.
- Fee is **preview-only**, not charged. The illustration excludes potential fee-related tax: obtain tax/accounting advice before enabling it.
- Every touched endpoint remains authenticated and PDS-workspace scoped; QuickBooks endpoints require `office_admin`.
- Existing financial data and locally modified `app/routers/data.py`, `data/users.json` are untouched.
- PDS has not yet confirmed the Intuit product edition/company or completed live Resend inbox delivery verification. Never assume a message arrived just because Resend returned an ID.

## Validation

- Local review: `1064 passed, 2 skipped, 3 deselected` in the available source archive.
- Three exclusions: two SDC smoke tests import `scripts/` excluded from the user-supplied source export; one supplier-quote test already failed on 5.66. Another six script-dependent test modules could not be collected in that archive; the local-Mac installer runs the full suite and includes those files.
- `node --check static/app.js` and Python compile: passed.
- Live browser/email/QuickBooks/Stripe transactions: **not tested**.

## What comes next after connecting accounts

1. Verify QuickBooks Online vs Desktop and authorized PDS company ID.
2. Map customer/vendor, income/expense items, taxable status, tax rates and existing transaction numbers; verify a single invoice and PO in read-only comparison mode before creating anything.
3. Select QuickBooks Payments vs Stripe (and Stripe Connect if SDC must receive transaction fees). Verify card and ACH availability and actual processing costs.
4. Confirm 0.5% fee customer disclosures, line-item tax treatment, SDC revenue contract/accounting, and whether it should apply to estimates, invoices and manual payments before enabling it.
5. Live-test a PDS estimate/invoice with Resend delivery-event verification, test payment link, signature-verified webhook, and no duplicate payment/ledger entries.
