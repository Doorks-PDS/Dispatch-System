# Doorks / Moses 5.57 — compact estimating, supplier RFQ, personal To-Do and unified save feedback

**Base:** Installed/committed Moses **5.56** (`Doorks_Moses_556_Job_Flow_ToDo_Fixes.zip`). This is an incremental patch only: **do not reinstall any earlier revision** and **do not apply if `git apply --check` fails**. No business data, customer media, credentials or Render settings are included.

## Changes

- **Photos in the Estimate/Invoice Helper:** Job and saved-form images now use one featured image and at most three small thumbnail buttons; previous/next arrows cycle through every image without horizontally scrolling a strip. Click the featured image to open the existing larger attachment viewer. Each saved form still retains its own photos.
- **`＋ New` beside Parts / Materials search:** Added to **both** the Moses recommendation helper and the full editable Estimate/Invoice generator. The existing catalog intake supports **Part / Product**, **Service / Subcontractor**, or **Supplier Quote Request**. Choosing a supplier request opens a genuine saved RFQ draft and does **not** insert a $0 catalog part or overwrite the unsaved estimate.
- **Supplier Quote Request forms:** The Moses Job Flow queue and quick intake are email-shaped: saved vendor selection and visible recipient, job number, subject, one scope/description box, a read-only configured PDS Reply-To, and PDF/image attachments. Supplier quote requests save as drafts. Staff review the actual email/attachments and explicitly approve any Resend send; uncertain send outcomes are held. Supplier pricing/quote number and lead time still arrive through the existing response workflow. The request itself is not a cost or inventory entry.
- **Personal To-Do badge:** Counts assigned quotes and only invoices explicitly assigned to the signed-in user; unassigned office-wide invoice review items remain visible on the To-Do page but do not inflate the nav badge.
- **Calendar:** Taller desktop day cells and tighter spacing permit at least five ordinary job rows where space allows. A day with approved time-off also accounts for that marker; the full list remains in the day drawer.
- **Save feedback:** Integrates the existing green **bottom-center** operation bar with PDS save handlers. A single bar now reads **Saving… → Saved!**, **Saved with warnings**, or **Save failed**. Removes the misleading `Request completed. Check the form for confirmation.` message and the duplicate top-right progress chip for these saves. Completion-form attachments and Door Records processing finish before displaying final completion status. Provider/email approval is **not** confused with a saved record.

## Install safely (Mac, `main` only)

Download `Doorks_Moses_557_Compact_Workflow_Save_Feedback.zip` into Downloads, then:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-557
unzip -o ~/Downloads/Doorks_Moses_557_Compact_Workflow_Save_Feedback.zip -d /tmp/doorks-557

git apply --check /tmp/doorks-557/moses_557.patch
# STOP if git apply --check reports any mismatch. Do NOT apply on a different base.
git apply /tmp/doorks-557/moses_557.patch

python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/doorks_operation_feedback.js
git diff --check
```

**Source validation on the supplied 5.56 base:** `975 passed, 2 skipped`; Python compilation and both JavaScript syntax checks passed. The local pytest runner used Python 3.13 and emitted multiprocessing-fork deprecation warnings only. Tests do **not** establish live browser behavior, Resend delivery or Render disk persistence.

## Git commands (only after tests pass)

```bash
git add static/app.js static/style.css static/doorks_operation_feedback.js \
  templates/ui.html app/routers/pds_supplier_quotes.py \
  tests/test_moses_548_calendar_fit.py \
  tests/test_moses_551_generator_quick_add.py \
  tests/test_moses_553_supplier_quotes_and_save.py \
  tests/test_moses_554_job_flow_calendar.py \
  tests/test_moses_556_jobflow_todo_regressions.py \
  tests/test_moses_557_compact_workflow.py \
  MOSES_557_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.57 - compact job workflow and unified save feedback"
git push origin main
```

## Live verification

1. From Moses Job Flow, open a job with multiple photos and navigate beyond the third photo; inspect full size.
2. Open the helper, choose `＋ New → Supplier Quote Request`, save an RFQ draft with a small attachment, then return to the unfinished estimate. Verify the request is in Supplier Pricing without a new $0 estimate line.
3. In both quote and invoice generators, create a part/service using the new button beside the search box.
4. Verify the PDS To-Do badge counts only your assigned work while Office Quotes & Invoices remain on the page.
5. Open November calendar dates with several jobs (including a time-off date); five rows should fit on typical desktop heights, with the remainder in the day detail.
6. Save a disposable Completion Form: one bottom-center status bar shows in-progress then actual success. Test an invalid save and an attachment error to see the appropriate failure/warning, not a false green success.
7. Send a **test supplier RFQ to an inbox you control** only after reviewing the explicit approval; verify delivery in Resend logs. No automated send or inbound reply matching is added.

No GitHub commit, Render deployment, data migration or external email send was performed while preparing this patch.
