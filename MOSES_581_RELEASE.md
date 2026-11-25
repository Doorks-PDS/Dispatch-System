# Moses 5.81 — reviewed QuickBooks line-item links (cumulative 5.72–5.81)

## New in 5.81

- QuickBooks Hub > Setup adds **Match invoice / PO line items**. Office Admin chooses a *prepared* invoice or supplier PO, reviews the exact saved lines, and can approve a numeric QuickBooks Item ID per line.
- Provider verification is **GET/read-only** against the exact connected company. Requires a unique, active QuickBooks item of a supported type (Service, NonInventory, Inventory); invoice item requires a valid **IncomeAccountRef**, supplier PO item requires a valid **ExpenseAccountRef**.
- The local approval is saved in `<DOORKS_DATA_DIR>/pds_qbo_line_approvals.json` using the existing atomic, locked, durable store. It includes company/environment, source fingerprint, line position, description/quantity/amount, accounting account reference and approval actor/time. No secrets are saved.
- Repeated approval of an unchanged ID is idempotent; conflicting IDs or stale source/company are blocked for Office reconciliation. Changing an invoice or PO after it was prepared invalidates its mappings; there is no automatic override.
- Document sync-readiness now reports approved line counts. **Even when all item lines are reviewed, `can_post=false`**; tax-code/jurisdiction, terms, current provider account verification, number collisions and supervised posting approval still require separate work.
- The QuickBooks item lookup and approval do **not** overwrite parts, prices, customers, vendors, QuickBooks records, or existing invoices/POs. PDS parts-master links from 5.78 remain separate; automatic suggestions/reuse of those links is future work.

## Carried forward unchanged

- 5.72–5.80 features: multi-recipient To/CC estimate/invoice email preparation, Save & Estimate forms, Office-only PO management, read-only PO access for leads/techs, QBO OAuth and verified company catalog, duplicate check, customer/vendor/supplier/part master links and party readiness.
- A **0.5% universal service fee remains a preview only**, never added to saved documents, emailed invoices, QuickBooks amounts, payment links or charges.
- QuickBooks provider transaction writes, automatic synchronization, Stripe/payment links and SDC transfers remain **disabled**.

## Testing and rollout boundary

- Cumulative source patch verified against the original Moses 5.71 (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`) source baseline.
- Available source archive tests: **1,133 passed, 2 skipped, 3 deselected**. Three deselections: one existing baseline supplier-part issue; two tests requiring `scripts/` omitted from the uploaded source archive. Six script-dependent test modules could not collect from the archive and must run on the full Mac repository.
- `node --check static/app.js`, Python compilation: passed. Live QuickBooks accounts, emailed estimates/invoices and payments **not tested**.
- **Not approved for production Render deployment.** Run the included safe installer and complete local/browser and controlled provider tests first.
