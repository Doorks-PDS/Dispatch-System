# Moses 5.73 — QuickBooks Online connection readiness, Office PO controls, and direct form-to-estimate handoff

## Baseline and installation

- This cumulative release is for `main` at **Moses 5.71** (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`).
- Includes all source changes from 5.72 **and** 5.73. **Do not install the separate 5.72 ZIP first.**
- Requires a clean Git working copy for the release's actual target paths. Existing unrelated changes and production data are not touched by the installer.
- No Render deployment, Git commit, email send, payment collection, or QuickBooks posting occurs in the installer.

## QuickBooks connection preparation (Online only)

- Intuit OAuth 2.0 authorization with state, authenticated Office Admin, short expiry, PDS workspace isolation, verified company realm, encrypted tokens and durable storage.
- Online company-info verification is **GET/read-only**. Initial connection does not create customers, invoices, POs, tax items, payment links, bills or payments.
- QuickBooks Hub displays exact readiness checks, verified company and pending field mappings for invoices/POs.
- Set `PDS_QUICKBOOKS_EDITION=online` if edition should be controlled by Render; otherwise choose Online in QuickBooks Hub.
- Register an Intuit app for the chosen environment (sandbox vs production), then configure these environment variables on Render (do not paste credentials into ChatGPT):
  - `PDS_QBO_CLIENT_ID`
  - `PDS_QBO_CLIENT_SECRET`
  - `PDS_QBO_REDIRECT_URI` — exact `https://YOUR_HOST/pds-quickbooks/oauth/callback` registered with Intuit
  - `PDS_QBO_ENVIRONMENT` — `sandbox` or `production`; start in sandbox
  - `PDS_QBO_TOKEN_ENCRYPTION_KEY` — generated Fernet encryption key; store securely and back up separately
  - `DOORKS_SESSION_SECRET` — strong random secret (at least 32 characters), not a sample/default
  - `DOORKS_DATA_DIR` — existing durable Render-backed data directory (not ephemeral source path)
- New dependency: `cryptography>=43,<48`. Install Python dependencies from `requirements.txt` in development/Render before using the connection.
- OAuth token file: `<DOORKS_DATA_DIR>/pds_qbo_connection.encrypted` (encrypted at rest). Keep the encryption key securely; do not rotate it blindly or tokens become inaccessible.
- Disconnect local account deletes stored local credentials only; it does not revoke access at Intuit. Revoke in Intuit separately if desired.
- **Still disabled:** QuickBooks invoice or supplier PO creates/updates, automatic syncing, payment links, reconciliation and Stripe/SDC revenue transfers. Mapping, subscription eligibility and live account tests remain for later setup.

## Purchase order role controls

- Staff (`tech`, `lead`) may view linked PDS supplier POs, read their list and print/download PDFs, including external business-scope PO references.
- Only `office` / `office_admin` may create, edit, track status, enter receiving, import supplier POs, run PO AI extraction or send vendor PO emails. `office_admin` retains PO deletion authority.
- Doorks and SDC saved PO collections likewise allow staff read, Office writes, while other collections retain their existing permissions.
- No PO content or linkage was deleted or rewritten.

## PDS completion / recommendation form shortcut

- Preserves **Ready to Quote**.
- Adds a compact **✦ Save & Estimate** button beside **Save Form**.
- Saves form and attachments first, verifies saved form ID against the refreshed PDS job, then opens the existing Estimate/Invoice generator at that exact form. No estimate is sent or auto-approved.
- If save fails, the estimator does not open. If attachment/door-log side effects fail, the existing warning remains and no automatic handoff occurs.

## Payments and customer email (carried forward from 5.72)

- Multiple To / CC recipients, saved customer-contact suggestions and reviewed Resend attachments.
- 0.5% service-fee plan applies across all payment methods, but **preview only**: saved invoices and QuickBooks handoff totals are unchanged. Tax treatment and commercial disclosures remain pending review.
- QuickBooks-ready *read-only* line-item sync previews preserve document numbers, amount fingerprints and mapping checkpoints.

## Validation

- `node --check static/app.js`, Python compilation and targeted QuickBooks/Purchase Order tests pass in the supplied source snapshot.
- Available regression suite: **1,070 passed, 2 skipped, 3 deselected**. Six script-dependent test modules cannot collect from the uploaded source-only archive and need a run on the full Mac checkout; one supplier-part test is a known 5.66 issue and is deselected.
- Live Intuit/Resend/Stripe API testing has NOT been done.
