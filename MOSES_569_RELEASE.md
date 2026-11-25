# Moses 5.69 — Technician Estimate and Invoice Review

**Cumulative package:** install 5.68 (which already contains 5.67), then 5.69. On GitHub main before installation: Moses 5.66, `530d6958b1973437e0879540a8b90baad5ea31e8`. Nothing is automatically sent or deployed by this package.

## Permission rules

- **Technician**: create, edit and save PDS Estimates (RE) and Invoices (JS); **never** create, edit or email supplier Purchase Orders. A saved document is not sent until reviewed by Office.
- **Technician document email**: the existing Email action is relabeled **Submit for Office Review**. This creates one idempotent pending document-email approval with original PDF hash, verified job and recipient. No Resend call or job status update occurs.
- **Office / Office Admin**: can open **Ready for Review**, view/edit, decline, or review and send technician requests using the exact existing Resend/PDF flow. Backend authorizes the send and verifies the latest saved document fingerprint; stale approvals are refused.
- **Lead**: existing estimate/invoice capabilities unchanged. Leads cannot approve or email a technician-submitted review request. No new lead approval requirement.
- **Quote Ready** / **Invoice Ready**: document review labels in the pending office queue, *not* new underlying job statuses. Sending an estimate still changes Quote to Quote Sent through the existing verified flow; invoices still use the existing eligible Complete-to-Done path. No premature status change.
- Both PDS **Job Flow** and **Moses Job Flow** expose Ready for Review; Moses Action Center gets a matching tab for eligible office roles. The exact shared document email approval path is reused, not a second sender.

## Source compatibility

Do not overwrite the current 5.66 `app/services/moses_pds_document_email.py` with an older snapshot. `apply_review_guard.py` deliberately inserts only the authorization/review fields into the installed source and preserves recent history, sent_quote_number, PDF verification and status safeguards. The script validates every anchor and fails without writing when the source doesn't match. Review and code changes are not deployed until you choose to commit/push.

## Tests and release

- 1,001 passed / 2 skipped in the reconstructed source run; JavaScript syntax and Python compile checks pass.
- Tests include technician permissions, impossible direct send, role-restricted queue, office approval, stale-PDF guard and unchanged PO prohibition.
- Unit tests are *not* live browser, OpenAI, Resend or QuickBooks acceptance. Keep Twilio send disabled pending A2P approval.
