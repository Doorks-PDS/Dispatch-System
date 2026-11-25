# Moses 5.74 — read-only QuickBooks catalog discovery

## Cumulative baseline

This bundle contains Moses 5.72, 5.73 **and 5.74** and targets the committed Moses 5.71 source (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`). Do **not** install 5.72 or 5.73 first. No Render deployment is required by the installer.

## Added in 5.74

- Office Admin-only QuickBooks Online catalog lookup in QuickBooks Hub > Connection setup.
- After Intuit authorization and verified company selection, browse the first 1,000 records in bounded 50-record pages: customers, vendors, items, accounts, tax codes and terms.
- Queries are fixed and use GET, with returned data limited to IDs, display names, types and relevant item/account references. The UI never creates mappings, customer records, invoices, purchase orders, payments or links. No catalog is cached in persistent storage.
- Company ID, environment, role and pagination are checked for each request. Provider errors never expose tokens to browser messages.
- Separate offline API-security tests protect the read-only behavior and role boundary.

## Retained from 5.72–5.73

- PDS estimate/invoice email To/CC selection and saved-customer-contact suggestions, approval-gated Resend send.
- Completion/Recommendation **Save & Estimate** after successful save; **Ready to Quote** remains.
- Leads and techs view existing POs; Office and Office Admin manage POs; deletion remains Office Admin only.
- QuickBooks invoice/PO handoff previews, numbering policies, encrypted QBO OAuth, read-only company verification.
- Proposed 0.5% service fee is **preview-only**, not applied to invoices and not collected.

## Still intentionally inactive

QuickBooks transaction posting, provider mapping writes, payment links, payment reconciliation, automatic sync and Stripe/SDC transfers are disabled pending provider/account verification, accountant review and explicit authorization.

## Verification

Static JavaScript syntax, Python compilation, all available source-archive regression tests passed with the previously documented exceptions: source-only archive omits `scripts/` needed by six collection modules and two SDC smoke tests, and one supplier test also fails on the 5.66 baseline. The installer runs the complete Mac checkout tests and will roll back release-file changes if they fail.
