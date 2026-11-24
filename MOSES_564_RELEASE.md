# Moses 5.64 — Cumulative Workflow Repairs

**Base:** origin/main `7b66104cc4f4026693c9c897970e659a01c35545` (Moses 5.63). This patch includes the repaired UI and API changes only. No production records, previously saved PDFs, receipt attachments, secrets or email settings are replaced.

## Repairs

- **Job ticket:** Eliminates the second five-choice **Alternate** menu; uses direct **Receipt**, **Packing Slip**, and a single **Attach Existing** link for previously issued documents. Original native Estimate, Invoice and Purchase Order buttons stay in place.
- **Estimate helper:** `+ New` now calls the existing Parts/Services quick editor whether launched from ticket, To-Do, or Moses Job Flow.
- **Estimate / invoice email:** Reuses the existing PDS document email templates, verified saved PDF, contact email, From / Reply-To, approval, Resend idempotency, and delivery history. A saved document opened from its verified job now identifies a stale Job # and requires office review and **SAVE** to regenerate the PDF before sending. Does not bypass customer/job matching and does not silently send/retry.
- **PO from ticket:** Fixes double opening that erased job/customer prefill. PDS PO editor now preserves the selected customer and links to an exact saved job, falls back to a focused job search, rejects mismatched customer names, and (when the job has no previous PO #) writes and verifies the saved PO number back onto the job. Existing PO numbers are preserved; old POs can be opened and edited instead of recreating them.
- **PO line items:** Removes duplicate selected-part text, uses existing part number/description, hides redundant unit column in PDS editor, and fills supplier cost when available from saved part data. **Customer selling prices are not used as supplier costs**; unavailable cost stays for manual review.
- **Dispatch / sales leads:** Quick date editor works for both job types. API now accepts `scheduled_date`; the save synchronizes calendar and scheduled date, rereads the saved job, refreshes the calendar, and preserves status and assigned technicians. Scheduler's existing **Update to Schedule** button is visible again.
- **Receipts and Accounting:** Existing receipt upload triggers the existing AI extractor on file selection; removes redundant **Upload Receipt / Read with AI** button. Missing/empty AI results display the true diagnostic rather than claiming successful extraction. Adds 🔔 pending receipt-authorization count to Accounting Hub and **Authorize** filter, highlights pending receipts first, provides a pending count on receipts dashboard, and uses smaller CSV export icons.

## Live provider configuration still required

- `MOSES_PDS_DOCUMENT_SEND_ENABLED=true` **on Render after this code is deployed** is required to permit approved estimate/invoice sending. This is separate from supplier Resend sender readiness and schedule notifications. Saving a document must not trigger email; a person must approve it.
- `OPENAI_API_KEY` must be configured for the existing `/receipts/extract` AI reader. Without it, the editor displays an honest unavailable message and allows manual entry.
- `PDS_SMS_SEND_ENABLED=false` until Twilio A2P approval and verified consent. Do not enable SMS in this release.

## Validation

- Local patch is generated directly against the exact current 5.63 GitHub `static/app.js` (blob `0b109dd16bfeed7fff26af782de4d5db1fe55b4d`), and current `app/routers/calendar.py` (blob `67236e776028328e3a648a04da3c2b3b9aa3cf53`).
- 30 focused regression tests passed in the reconstructed local test environment.
- Python compile, JavaScript syntax checks, and `git apply --check` performed.
- The uploaded full source snapshot's old tests contain obsolete UI expectations from pre-5.63; a full current-GitHub test suite must be run on your Mac before pushing.
- Live browser, sending, existing mismatch remediation, PO supplier price mapping, and real receipt AI call have **not yet been verified**. No emails or business changes were executed from this release.
