# Moses 5.78 — PDS/QBO master record linking

## Cumulative scope

Includes Moses 5.72–5.78 changes, based on committed Moses 5.71 (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`). This replaces earlier *uninstalled* packages.

## New: reusable identity links

- QuickBooks Hub now lists existing PDS customers (CRM), PDS service vendors and PDS parts/services alongside their company-scoped approved QBO IDs.
- Office Admin can inspect QBO catalog candidates and explicitly approve one ID against an exact-name, active QBO record. Approval uses read-only QBO queries and an atomic local ledger in the existing persistent Doorks data directory.
- Name changes, provider-company changes and duplicate local-to-provider assignments require manual review instead of silent remapping.
- Approvals remain reusable metadata; downstream transaction adapters **do not yet consume the master links**, and this update does not create/update invoices, POs, customers, vendors or items in QBO.
- Material suppliers named only on POs and not saved to the PDS service vendor list still need a proper master-record source and mapping step. Do not treat a supplier name alone as a unique identity.
- QuickBooks Desktop is not supported by this OAuth catalog integration.

## Current accounting position

QuickBooks Online authorization, read-only catalogs, prepared-document duplicate checks and document party approvals are included from earlier revisions. Customer/vendor/part links still need account, tax, item and document-posting approval before transactions sync. A proposed 0.5% fee is **not** charged or transferred. No payment link integration is live.

## Verification

- New targeted tests: 7 passed.
- Available source archive: 1,090 passed, 2 skipped; two tests unavailable due to missing `scripts/` directory; one preexisting supplier-parts fixture deselected. Six modules also fail import without `scripts/` and were omitted from this source-only run.
- Python compile, JS syntax, patch integrity and cumulative baseline `git apply --check` checked.
- Full Mac checkout tests and integration authorization still required before deployment.

## Deployment

**HOLD** until the Mac installer passes and live PDS data/email/permissions can be checked in a controlled rollout. Nothing in this package enables financial transaction or payment posting.
