# Moses 5.61 — Saved documents inside Job Flow

Base: **Moses 5.60**, including all changes through 5.60. Install on top of current main; do not reinstall 5.58/5.59/5.60.

## Job Flow
- Quotes and Invoices keep a job in the queue after the numbered estimate/invoice is **saved**; the queue no longer drops an invoice merely because `invoice_number` exists.
- For a verified linked saved document, show its number and **View/Edit** and **Email** actions instead of another draft button. Multiple linked documents remain individually reviewable.
- **View/Edit** opens the existing PDS editor; **Email** opens the existing verified PDF + saved job contact email + explicit Resend approval preview. No other email flow is added.
- After saving or an approved provider-accepted send, refresh the Job Flow documents and status, without automatically sending from document creation.
- Documents match by job ID or unique job number fallback **plus customer**, rejecting unrelated documents, mismatched job IDs, and unreconciled fallback PDF records.

## Status transitions
- Saving an estimate/invoice leaves job status unchanged.
- Only after an approved Resend send is accepted: **Quote / Complete-Quote / To Be Quoted → Quote Sent**, and populate `sent_quote_number` only if blank, without overwriting original `estimate_number`.
- Only after an approved Resend send is accepted: **Complete / Complete-Quote / To Be Invoiced → Done** for an invoice. Unfinished jobs are never marked Done by merely emailing a PDF.
- Resend acceptance is not inbox delivery. If status synchronization fails, the email remains sent and status is flagged for office review; never retry automatically.
- Existing approval and `MOSES_PDS_DOCUMENT_SEND_ENABLED` gate are unchanged: ensure gate, sender and permissions are configured before live testing.

## Verification
Source regression: **1,003 passed, 2 skipped**. No external emails sent in testing. Browser acceptance still needed.

## Local install
```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-561
unzip -o ~/Downloads/Doorks_Moses_561_Job_Flow_Document_Followthrough.zip -d /tmp/doorks-561
git apply --check /tmp/doorks-561/moses_561.patch
git apply /tmp/doorks-561/moses_561.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```
Only apply when the check passes. No production business data is changed by this patch installation.

## Git
```bash
git add static/app.js app/services/moses_pds_document_email.py \
  tests/test_moses_38_interface.py tests/test_moses_42_workflow.py \
  tests/test_moses_45_direct_workflows.py tests/test_moses_47_queue.py \
  tests/test_moses_554_job_flow_calendar.py \
  tests/test_moses_561_job_flow_document_followthrough.py MOSES_561_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.61 - saved Job Flow documents and email follow-through"
git push origin main
```

## Live acceptance
1. Quote job: create and save RE; re-open Job Flow → Quotes: same job with View/Edit and Email (no duplicate Draft).
2. Email to **verified test contact only** → approve; confirm Resend accepts it and job becomes Quote Sent, `sent_quote_number` updated. Job leaves quote queue.
3. Completed job: create and save JS; re-open Job Flow → Invoices: View/Edit and Email. Approve test send; confirm Done and job leaves invoice queue.
4. Check linked customer address, PDF and resend delivery history; no automatic send from draft or edit. Do not send live customer messages during tests without approval.
