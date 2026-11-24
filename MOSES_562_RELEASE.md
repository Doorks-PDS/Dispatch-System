# Moses 5.62 — To-Do List direct actions

**Base:** Moses 5.61 on `main`. Includes and preserves all prior Job Flow, saved-document, email, supplier RFQ, PIN and calendar revisions. This is a source-only patch; no business records or email credentials are included.

## PDS To-Do List
- Replace the old **◉ Moses** card shortcut in the visible PDS office To-Do List with direct actions:
  - Quote: **View Job · Request Supplier Quote · Draft Estimate**.
  - Complete/Quote: **View Job · Request Supplier Quote · Draft Estimate · Draft Invoice**; staff choose the intended document.
  - Invoice-only queue: **View Job · Draft Invoice** (no supplier-request button).
- **Request Supplier Quote** opens the existing supplier request form directly for the saved job and saves a Draft only; does not email the supplier.
- **Draft Estimate / Invoice** opens the existing recommendation/helper (including saved job photos, parts search and + New) rather than a new editor.
- When a verified matching document is saved, show **View/Edit Estimate/Invoice** and **Email Estimate/Invoice**, reusing 5.61's document matching and approval-controlled Resend email panel.
- Job Details and document drawers close back to the existing To-Do List. Refresh the task cards after saving or a confirmed send.
- The office-wide invoice review section and personal To-Do notification count are unchanged.
- Saving documents does not send them or change job statuses. Existing 5.61 approved-send status rules remain unchanged. Twilio remains disabled pending campaign approval.

## Verification
- **1,006 passed, 2 skipped** in source tests. JavaScript syntax validated.
- No live customer emails, supplier RFQs, invoice payments or job record changes were made as part of testing.
- Browser acceptance still required for layered drawers, To-Do List refresh and document email contact validation.

## Install (5.61 must already be applied)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-562
unzip -o ~/Downloads/Doorks_Moses_562_ToDo_Actions.zip -d /tmp/doorks-562
git apply --check /tmp/doorks-562/moses_562.patch
# Only if --check returns without errors:
git apply /tmp/doorks-562/moses_562.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Commit/push (after tests pass)

```bash
cd ~/doorks-deploy-edit
git add static/app.js \
  tests/test_moses_45_direct_workflows.py \
  tests/test_moses_562_todo_actions.py \
  MOSES_562_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.62 - To-Do direct supplier and document actions"
git push origin main
```

## Acceptance
1. PDS To-Do List, assigned Quote: View Job, Request Supplier Quote, Draft Estimate visible. Close Job Details; To-Do List remains.
2. Create a supplier RFQ draft and cancel/suspend before sending. Confirm job number is attached; no supplier email is sent.
3. Complete/Quote offers both Draft Estimate and Draft Invoice; neither is generated automatically.
4. Save an estimate/invoice to a test job; To-Do card refreshes to View/Edit + Email. Close editor; To-Do remains.
5. Use only a controlled test recipient with explicit approval to verify saved document email; confirm status changes only after accepted send.
