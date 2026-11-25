# Moses 5.70 — QuickBooks Hub: polished dashboard + supplier PO review

**Cumulative base:** GitHub `Doorks-PDS/Dispatch-System` `main` at Moses 5.66, `530d6958b1973437e0879540a8b90baad5ea31e8`. **5.67, 5.68, and 5.69 have not been deployed yet.** This package contains those earlier patch steps plus the new 5.70 patch. No branch, new Render service, live sync, keys, supplier emails, or automatic deployment.

## QuickBooks Hub design
- Clean, responsive PDS QuickBooks Hub under Accounting Hub; **Office Admin only**, enforced in frontend and on every API route.
- Readable finance hero, invoice/PO queue counts, unresolved review counts, four-step sync readiness indicator, and `Invoices`, `Supplier POs`, `Activity`, `Setup` tabs.
- Search and filter each queue; show supplier, job, date, status, total and exact reason a record is blocked; explicit `Prepare handoff` confirmation; separate exports and joined activity history.
- Display **Not connected** and **Not synced** accurately. No fake QuickBooks credentials or automatic/authorized sync claims.

## Supplier PO handoff (not a live QBO/QuickBooks Desktop connector)
- `GET /pds-quickbooks/purchase-orders` lists saved **PDS supplier** purchase orders separately from customer PO numbers and customer invoices.
- Backend validates unique `PO-000xx` number, saved PO ID, vendor, unique verified PDS job/customer, `Ordered` or later status, positive quantities, supplier costs, tax and shipping, and matching saved total.
- Orders not emailed to a supplier can still qualify **once their recorded status is Ordered or later**; an email alone does not create a QuickBooks entry.
- Draft/cancelled/missing-job/invalid-total POs cannot be prepared. Legacy stock purchases without a PDS job are flagged for review (future stock workflow), not silently attached to customers.
- `POST /pds-quickbooks/prepare-po` explicitly stages one immutable, fingerprinted record; repeat calls are idempotent. Editing a previously prepared PO invalidates its staging until manually reconciled. No automatic mutation of supplier PO, job ticket, invoice, customer PO, inventory, receiving, payments, or QB ledger.
- `GET /pds-quickbooks/po-review.csv` exports validated prepared PO review records with spreadsheet formula escape protection.
- Invoice handoffs now flag a previously staged invoice modified afterward as `Changed — Review Required`.

## QuickBooks accounting safety and next real connection step
- **No Intuit OAuth, QuickBooks API calls, Desktop Web Connector, external bookkeeping writes, or inventory changes** are part of this patch. This release makes the UI and staging data capable of being connected in the next phase.
- QuickBooks Online: identify the actual PDS company/plan, configure secure Intuit OAuth in Render, map customers/vendors and items/expense accounts, check taxes, reconcile existing invoices/POs, run one reviewed test. PO availability in QuickBooks Online depends on the subscription tier (Intuit documents Plus/Advanced). No API token in GitHub or ZIP.
- QuickBooks Desktop: confirm the Windows Desktop edition/year and Web Connector version, then establish a supported service connector to the existing backend; daily exports need not be manual once configured, but Windows QuickBooks must be available.
- Purchase orders are purchasing commitments; accounting liability and inventory/receiving require separate supplier-bill/receipt workflows.

## Installation / QA
- One ZIP contains 5.68 cumulative-on-5.66, 5.69 UI patch and safe document-email guard, plus 5.70 PO/visual patch and unified install script.
- On reconstructed 5.69 source: **1,025 tests passed, 2 skipped**. Checked `node --check static/app.js`, `node --check static/moses_action_center.js` and Python compile. Tests are local only; live QuickBooks sync not exercised.
- Local install only; Git commands provided but not executed here. **Do not apply against an unexpected Git HEAD or force-apply on conflicting local modifications.**
