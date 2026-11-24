# Moses 5.63 — Action Center refresh

**Base:** Moses 5.62, installed locally. If 5.62 is not yet pushed, apply this patch over 5.62 and commit both together for one Render deployment.

## Action Center
- Replace accordion/dropdown groups with clean tabs and searchable job-style cards: **Jobs · Drafts · Approvals · Delivery · Texts** (PDS). Doorks/SDC retain workspace-specific **Approvals · Delivery** only.
- Give Moses Action Center a wider, centered panel on desktop; keep mobile a single usable full-height panel. No new service, separate backend, or second document editor.
- PDS Job cards show the **customer, job number, status**, then direct **View Job**, **Request Supplier Quote**, **Estimate**, **Invoice**, and **Ask Moses** actions as appropriate for that saved job's status. **Complete/Quote** supports both estimate and invoice; invoice-only work does not get the supplier button. Parts follow-up can request supplier pricing.
- Estimate/Invoice opens the existing verified PDS document: if an exact saved document is associated with this job and customer, open that editor; otherwise open the same recommendation/helper used by Job Flow. Existing email approval stays in the document workflow.
- **Open Full Job Flow** opens the existing Job Flow queue for all jobs, not a copy. Action Center's server-provided preview remains capped at 12 items per section; tab counts report the actual saved queue counts.
- Preserve Moses Draft review, separate estimate scopes, approval queue and explicit SMS approval/decline. Secondary tools appear on the job card, not in a top-level dropdown.
- Keep action requests scoped to the active authenticated workspace; PDS job events are guarded by the existing PDS office roles. No automatic document save, email, SMS or status mutation.
- Bump `moses_action_center.js` asset URL to `v=5` to ensure browsers use the updated action UI.

## Verification
- **1,009 tests passed, 2 skipped** (source tests; some existing multiprocessing deprecation warnings).
- JavaScript syntax checks passed for `static/moses_action_center.js` and `static/app.js`.
- Isolated Node regression verifies action events reuse a saved estimate, open the invoice helper when unsaved, link supplier RFQ to the exact job, and ignore invalid IDs or wrong workspaces.
- Live browser acceptance remains necessary for overlays, tablet layout and the production records.

## Local install (5.62 must be applied first)
```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-563
unzip -o ~/Downloads/Doorks_Moses_563_Action_Center_Refresh.zip -d /tmp/doorks-563
git apply --check /tmp/doorks-563/moses_563.patch
# Only if no errors:
git apply /tmp/doorks-563/moses_563.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_action_center.js
git diff --check
```

## Commit and push (after checks and review)
If 5.62 remains uncommitted, stage its changed files **along with** these changes and push them together. Otherwise, stage only the 5.63 paths below.
```bash
git add static/app.js static/moses_action_center.js templates/ui.html \
  tests/test_moses_38_interface.py \
  tests/test_moses_563_action_center_ui.py MOSES_563_RELEASE.md
# If 5.62 was not committed, also stage:
# git add tests/test_moses_45_direct_workflows.py tests/test_moses_562_todo_actions.py MOSES_562_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.63 - clean Action Center and direct Job Flow actions"
git push origin main
```

## Browser acceptance
1. Open PDS Moses → Action Center: visible tabs/cards, no accordion queue; search and counts work.
2. Open a Quote job → View Job; close ticket and return to Action Center. Request Supplier Quote opens the existing RFQ draft, never sends automatically.
3. Open a Complete/Quote job → both Estimate and Invoice actions available. Saved document opens editor rather than generating a second document.
4. Open Full Job Flow → original Jobs/Invoices/Supplier Pricing queue works.
5. Open Drafts, Approvals, Delivery and Texts; verify controls work through the existing approval backend. SMS stays disabled pending Twilio approval.
6. Switch to Doorks/SDC and verify only their own approved queues appear. Confirm mobile/tablet layouts.

No production data, API keys or environment switches are included. No GitHub push or Render deployment performed.
