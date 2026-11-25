# Moses 5.76 — read-only QuickBooks customer/vendor name review

## Cumulative installation

This release **includes 5.72, 5.73, 5.74, 5.75 and 5.76** on top of the committed 5.71 baseline (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`). No need to install previous uninstalled revisions. The installer refuses unknown or locally modified release targets.

## Changes

- QuickBooks Hub > Connection setup adds **Review customer / vendor match** for an already prepared invoice or supplier purchase order.
- Compares the *exact, case/whitespace-normalized name* on the PDS document to a bounded page of Customer or Vendor records in the **verified** QuickBooks Online company.
- Displays provider record IDs for manual Office Admin review. A second record with the same name can exist; neither a single match nor a no-match response authorizes synchronization.
- No fuzzy matches, automatic linking, saved mappings, accounting writes, or new exposure to leads/techs. Paging remains bounded to 1,000 provider records and indicates when more pages remain.
- QuickBooks invoice/PO posting, service fee charging, payment links and SDC fee transfers remain **disabled**. The proposed universal 0.5% service fee is unchanged.

## Verification

- New focused tests: 3 passed, plus prior QuickBooks-specific tests: 27 passed.
- Available archive suite: 1,076 passed, 2 skipped. Two failures and six collection errors require `scripts/` omitted from the uploaded baseline archive; these run on the full Mac checkout.
- No live Intuit, Resend, Stripe, or Render actions were performed.

## Deployment recommendation

**Hold production deployment.** First install the cumulative patch in the 5.71 Mac checkout and pass its complete local suite. Then verify the QuickBooks company and a controlled invoice/PO/email workflow; do not enable live posting before account mapping and financial approval.
