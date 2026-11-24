# Doorks / Moses 5.56 — Job Flow + To-Do Follow-Up

**Apply to Moses 5.55.2** source, after the successful router fix. This is a narrow incremental source patch, not a full project. The 5.55 Supplier Pricing backend, approvals and durable attachment storage are reused. Nothing is emailed or issued by installing this patch.

## Changes

- Moses Job Flow tabs: **Quotes → Invoices → Supplier Pricing**.
- Invoice cards have no **Request Supplier Quote** button. Quote cards open a real saved supplier-request editor *over the current queue*, with job # prefilled, supplier selection, scope, qty, dimensions, subject, email message, and image/PDF uploads. They no longer navigate away to the Supplier Pricing tab just to begin a request.
- Saved RFQ drafts appear in Supplier Pricing, where the pre-existing **Review Email & Send** / explicit Resend approval workflow remains mandatory. Submitting a draft does not send email.
- **View Job** from the estimate/invoice helper opens a stacked job ticket without removing the unsaved helper. Closing the ticket restores the same draft.
- Reference panel now shows **Job Photos** from job attachments *and* form-specific thumbnail carousels. Click a thumbnail to open the existing full-size viewer.
- Removed the unwanted **Search and click a part…** helper instruction.
- **New Part or Service** gets a **Supplier Quote → Request Supplier Quote** action, opening a similarly structured RFQ form without discarding the current part/estimate draft. Draft RFQ ID is linked to the part when the catalog entry is saved. A supplier quote does not change customer price or inventory automatically.
- Visible **PDS To-Do List** gets a notification badge for actionable assigned quotes and office invoices; tech/lead assignments use the existing assigned-job endpoint. The old hidden To-Do List badge no longer receives the only count. A failed general Notifications fetch does not suppress the To-Do badge. Invoice badge and office To-Do share the same status-selection helper.

## Safety

- No source patch file contains production data, API keys, customer documents or saved attachments.
- The RFQ request form checks 8-file / 12 MB totals and the existing server enforces 4 MB per file, approved file types and role permissions.
- Save **Draft** first. Email preview, explicit Resend approval, and manual recording of supplier replies remain separate. No automated email-matching or pricing changes.
- Tests are source and server unit tests, not authenticated browser or live Resend acceptance. Verify the workflow using a test supplier/inbox before any real send.

## Installation (Mac, main branch only)

Place `Doorks_Moses_556_Job_Flow_ToDo_Fixes.zip` in Downloads, then:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-556
unzip -o ~/Downloads/Doorks_Moses_556_Job_Flow_ToDo_Fixes.zip -d /tmp/doorks-556

git apply --check /tmp/doorks-556/moses_556.patch
```

**Only if the check has no errors:**

```bash
git apply /tmp/doorks-556/moses_556.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Commit / push (after local acceptance)

```bash
git add static/app.js \
  tests/test_moses_45_direct_workflows.py \
  tests/test_moses_47_queue.py \
  tests/test_moses_554_job_flow_calendar.py \
  tests/test_moses_5552_nav_order.py \
  tests/test_moses_556_jobflow_todo_regressions.py \
  MOSES_556_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.56 - job flow RFQ and To-Do fixes"
git push origin main
```

## Live acceptance

1. Quotes / Invoices / Supplier Pricing order; Request Supplier Quote only on Quotes.
2. Quote request immediately opens input form; save with test supplier and small image/PDF; verify it appears in Supplier Pricing as Draft and no email was sent.
3. From New Part, open supplier request, then return to the still-open part form with its fields preserved.
4. Start an estimate/invoice, fill hours or line items, click View Job, close Job Details; confirm original values remain.
5. Open recommendation source; inspect both job-level uploads and photos from the selected form, and enlarge an image.
6. PDS office To-Do List badge should show open invoice(s) and your assigned quotes, not just completed calendar work. Confirm count updates after changes.
7. Check Safari desktop/tablet layout and the approved supplier Resend workflow with a controlled test inbox.
