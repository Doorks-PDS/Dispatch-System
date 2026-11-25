# Moses 5.71 — QuickBooks numbering and reconciliation readiness

**Cumulative baseline:** `Doorks-PDS/Dispatch-System` `main` at Moses 5.66 (`530d6958b1973437e0879540a8b90baad5ea31e8`). The delivery ZIP contains the previously **unapplied** 5.67–5.70 steps plus this **5.71** addition. This is an installation package for the user's Mac, **not** a live QuickBooks integration, and nothing was pushed/deployed by the assistant.

## PDS document numbering policy
- New `Numbering` tab in the existing PDS **QuickBooks Hub**. Designed to match the 5.70 dashboard; mobile-responsive document cards and a concise integration checklist.
- Separate policies for **estimates** (`RE00001+`), **invoices** (`JS00001+`) and **supplier purchase orders** (`PO-00001+`):
  - **Request same Doorks number** where the selected QuickBooks company supports custom numbering and the number is available.
  - **Let QuickBooks assign number** while retaining the original immutable Doorks document number.
- QuickBooks Online's `DocNumber` behavior depends on `Preferences.CustomTxnNumber`. **This is not verified yet** against PDS's company. Desktop uses SDK reference numbers and also needs edition/version confirmation. Neither numbering choice attempts an Intuit API call.
- Existing PDS estimates/invoices, PDFs, email history, document numbers, supplier POs, *customer* PO numbers, job tickets and account data are never renamed or modified by selecting a policy.
- Numbering policy is a separate JSON settings file stored under PDS's existing configured persistent `data_dir`, written atomically, with an Office Admin user ID and timestamp. No browser localStorage or temporary Render disk.
- A future-only server-side adapter hook records verified QuickBooks company/transaction IDs and their external display numbers. It rejects unverified calls, nonexistent/ambiguous PDS records, inconsistent remaps, reused provider transaction IDs and repeated external document numbers. **No public API route to assert synchronization**; the adapter must verify the provider object. Payment reconciliation should match provider IDs, not just display numbers.

## QuickBooks Hub experience
- Polished Numbering tab describes why PDS `JS00021` can coexist with a QuickBooks invoice such as `17566` without creating a second invoice or renumbering original PDFs.
- Separate estimates/invoices/supplier PO strategies, save confirmation, clearly labeled example values, future provider-verification counts, and checklist for custom-numbering settings, collisions, customer/vendor and item mapping, and eventual payments.
- Existing Invoices / Supplier POs / Activity / Setup tabs unchanged. `Not connected` and `Automatic sync off` remain accurate. Supplier PO numbers remain distinct from **customer** PO numbers.
- **Office Admin only:** all new read/write routes enforce PDS workspace + office_admin server-side; no technician, lead or office access.

## Important boundaries
- No OAuth, Web Connector, automatic transaction creation, estimate export, payment writeback, vendor bill, tax return calculation, inventory mutation or bank access in this release.
- Before actual sync: confirm whether PDS uses QuickBooks Online or Desktop and version/subscription, authorize the right company, verify numbering preferences and existing-number collisions, reconcile customer/vendor/items/sales tax, then test a single invoice and PO with read-back. Do not write API keys to GitHub.
- A prepared local handoff is not a synchronized QuickBooks transaction.

## QA and installation
- On reconstructed 5.71 source, **1,037 pytest cases passed, 2 skipped**, including 12 additional 5.71 tests. JavaScript syntax and Python compilation checks pass.
- Apply over the exact 5.66 baseline via `install_and_test.sh` in the cumulative ZIP. Its preflight checks all patch steps on a temporary copy before editing `~/doorks-deploy-edit`.
- Preserve all unrelated local files and business data. `stage_paths.txt` enumerates only edited/new source files. Commit/push is explicitly separate and manual.
