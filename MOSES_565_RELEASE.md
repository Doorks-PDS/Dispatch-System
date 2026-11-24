# Moses 5.65 — PDS customer documents, Alternate and purchase-order follow-through

**Baseline:** GitHub `Doorks-PDS/Dispatch-System`, `main`, commit `3cda6f8aa96f142c839cda9e7288dbe11a8d52bc` (5.64). Apply after 5.64, not to earlier revisions. This is a small cumulative patch; do not replace the project directory.

## Changes

- Restore the original **Alternate** ticket button and retain the existing ticket action buttons. Alternate offers only **Estimate, Invoice, Purchase Order, Receipt, Packing Slip**. The first three route through the existing Document Library upload/review/AI capabilities; the latter two use the established receipts register, upload and AI-extraction route. Nothing is issued automatically.
- Accounting Hub's pending receipt authorization count now uses the **same numeric badge** convention as the other navigation buttons. Receipt detail pages and authorization actions remain intact.
- Ticket document list labels an unsent saved estimate or invoice **Saved PDF**, not **Quote Sent**; shows **Email Sent** only when the existing PDS document delivery ledger confirms a sent action. Provides **View/Edit** of a saved numbered document from its job ticket.
- For an existing numbered estimate/invoice with a stale job number, opening **View/Edit** from the verified linked job copies the current job number into the editor for review. The user must SAVE to regenerate the **same numbered PDF** before using Email. It does not create a new estimate, overwrite the original Estimate #, bypass matching checks or claim an email was sent.
- The email review still uses the established PDS Resend template, sender, Reply-To, signed delivery history and explicit **Approve & Send**. The review now detects when `MOSES_PDS_DOCUMENT_SEND_ENABLED` is off and gives a direct edit action on a linked-job mismatch. No automatic retries of ambiguous deliveries.
- PDS purchase orders carry **verified PDS job ID and job number** to the existing PO register. Saving from a job ticket no longer depends on later browser-side linking. Multiple POs per job are displayed on the job ticket. The old single `po_number` ticket field is set for the first PO, without overwriting a previous value.
- PO editor and PO view retain existing line items, supplier pricing, vendor data and PDF. Added PO **status**, **tracking number** and **expected arrival**. Status choices: Draft, Ordered, Shipped, En Route, Delivered, Received, Cancelled. Manual order tracking is independent of email sending; **Received** requires recorded receiving quantities, not simply an email or delivery estimate. Older imported statuses remain editable without forced rewriting.
- Existing PO email process, PDF, recipient verification, approval and delivery journal remain in place. No automatic send when a PO is saved. A PO can be ordered outside the app and manually tracked.
- Adjusted outdated source assertions in prior tests to match the existing 5.63/5.64 Job Flow and To-Do layout. Added specific PO linkage/receiving/Alternate/document safeguards tests. No app business history, customer, supplier, payroll or payment data included in this patch.

## Render environment

The existing `Dispatch-System` service's environment was **merged** with:

- `MOSES_PDS_DOCUMENT_SEND_ENABLED=true` (estimates/invoices; still requires explicit approval)
- `MOSES_PO_SEND_ENABLED=true` (purchase orders; still requires explicit approval)

That environment update triggered a rebuild of **5.64**, not a 5.65 code deploy. Verify it reaches **Live**. `MOSES_EMAIL_PROVIDER=resend`, verified sender and `RESEND_API_KEY` must remain properly configured; do **not** copy secret credentials into source. Twilio outbound SMS remains disabled.

## Live acceptance checklist

1. From job **100344**, open saved estimate **RE00097** → **View/Edit**; confirm saved job/customer and correct Job #, save the **existing** estimate number (rebuild PDF). Close, reopen Email. Verify `To`, From, Reply-To, attached PDF; explicitly approve a controlled self-test. Check delivery history and Quote Sent only after Resend acceptance.
2. Repeat once with a saved invoice from a completed job; check status changes to Done only after provider acceptance.
3. Open existing PO (for example a test PO currently showing **00-0000**) → Edit → select verified saved job **100344** and matching customer → Save; check the PO appears under that job's Estimates/Invoices/POs, without making a duplicate PO. New PO from the ticket should be linked immediately.
4. Track a separate test PO from Draft → Ordered → Shipped → En Route → Delivered, with tracking number and expected date. Verify Received requires a recorded receipt, and confirm receiving increments quantity only once.
5. Confirm approved PO email to a known supplier using the existing manual review. Check Resend provider receipt and avoid retries of uncertain outcomes.
6. Verify Alternate offers exactly five document uploads, original job buttons are still present, and receipt AI extraction still works when API key is available.
7. Verify Accounting Hub notification is the familiar number badge. Check the previously approved receipt tickets and no loss of financial data.

## Source checks

The reconstructed 5.64 source + 5.65 patch passed `pytest -q tests/`: **957 passed, 2 skipped**; Python 3.13 raised only multiprocessing fork deprecation warnings. JavaScript syntax and `git diff --check` passed. This test count may differ on the owner's Mac due to additional local tests. The patch also has an isolated `git apply --check` verification. No live end-to-end delivery is claimed by source tests.
