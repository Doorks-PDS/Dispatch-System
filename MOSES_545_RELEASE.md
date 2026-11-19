# Doorks / Moses 5.45 — Consolidated Field, Office & Business Flow

**Incremental patch for source version 5.44 only.** It contains changed application code, two test files, and release scripts only. No PDS customer files, production database, backups, credentials or Render configuration are included.

## Completed in this source revision
- Field Flow label and purpose icons for Job Flow, Office Flow, Field Flow.
- Door Records: appropriately sized Save button and draft-only Moses reader for notes, dictated text, images, and PDF. Review/apply before Save. Source AI configuration still required in live PDS.
- Dispatch: Job Actions grouped visually before the Scheduler; former staff are excluded from assignable roster even if an old login is still active. Historical assignments are not rewritten.
- Vehicle Flow: compact Save Vehicle button, single vehicle-info toggle, next-service date in card subtitle, and current **fleet-wide physical quantity** shown on each saved standard template item. Does not turn template targets into warehouse stock.
- Accounting: Inventory opens first; Receiving is a separate tab with Pending/Partial, Received, Rejected/Cancelled and All filters; received POs do not clutter the landing page; administrator may delete an **unreceived** incorrect PO after explicit confirmation; any PO with receiving history cannot be deleted.
- Business Hub: Document Library last, now scoped to business with categorized upload types for estimate/invoice/PO attachments, packing slips, receipts, suppliers, customers and parts references. Job number and PO number recorded as references; **these are not official document issuance or inventory postings**. Add Part with Moses opens the existing PDS parts editor.
- PDS Business Settings: routes to existing billing defaults and document editor, without duplicating pricing storage.
- Accounting Settings: expense categories and links to existing receipt and inventory controls.
- Receipts: tech/lead lists are their own uploads (ID ownership for new records; name fallback for historic records). Office can still review records behind accounting authorization.

## Installation / tests

Check baseline **before** unzipping files into your working tree:
```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-545-check
unzip -o ~/Downloads/Doorks_Moses_545_One_Cumulative_Flow_Repair.zip \
  scripts/check_moses_545.py scripts/moses_545_manifest.json -d /tmp/doorks-545-check
python3 /tmp/doorks-545-check/scripts/check_moses_545.py --root "$PWD" --phase before
```

On PASS:
```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_545_One_Cumulative_Flow_Repair.zip -d .
python3 scripts/check_moses_545.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

**Locally verified:** 905 passed, 2 skipped on Python 3.13; browser, provider and Python 3.11 environment checks on your Mac still required. A mismatch in the before checker means stop and reconcile your local code, not overwrite newer changes.

## Git commands — execute yourself ONLY after successful verification
```bash
cd ~/doorks-deploy-edit
git add static/app.js templates/ui.html \
  app/routers/pds_scheduling.py app/routers/pds_purchase_orders.py \
  app/routers/receipts.py app/routers/document_vault.py app/routers/door_logs.py \
  tests/test_pds_543_ui_routes.py tests/test_moses_545_cumulative_workflows.py \
  scripts/check_moses_545.py scripts/moses_545_manifest.json MOSES_545_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Doorks Moses 5.45 - consolidated field office and inventory flows"
git push origin main
```

Do **not** run `git add .`; protect local `.venv`, data and backups. Your push can automatically trigger the live Render deployment. This package does not deploy itself.

## Live acceptance checklist
1. PDS home, calendar, ticket and saved jobs load, including a historic scheduled job. Action buttons are grouped under Job Actions.
2. Scheduler staff excludes inactive profiles. Past tickets retain historical assigned names.
3. Door Records Save is compact. AI note/photo/PDF preview requires a working OpenAI key and does not save until you approve and click Save Door Record.
4. Vehicle Flow ticket has one Vehicle Info button, compact save, a next-service date, and fleet totals equal the sum of physical quantities across active van tickets.
5. Accounting > Inventory & Receiving opens Inventory first; search stock, then switch to Receiving. Verify Pending, Received, Rejected/Cancelled filters and that history persists.
6. Try Delete Unreceived PO only on a disposable test PO; verify no auto-delete of received POs.
7. Business Hub Document Library last, upload a part reference with job/PO number; confirm it appears in business library but does not create a part or an accounting entry. Use Add Part with Moses for actual Parts List creation.
8. Business Settings opens existing billing controls; Accounting Settings opens expense categories. Save only when authorized.
9. As a tech/lead, receipt history displays only their uploads, and an other-user receipt file is denied. Office remains accounting-authorized.
10. Ask Moses for today's dispatch, van shortages, separate estimate scopes, and an unsent appointment-email approval. These are **live validations**; this patch does not certify full AI execution or email/SMS delivery.

## No claims of automatic financial reconciliation
Inventory and van quantities are operational records. This patch doesn't create verified COGS, tax deductions, bank transactions or QuickBooks migration parity. Resend/Twilio provider tests remain separate and must be approved before live outbound sending.
