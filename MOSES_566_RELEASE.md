# Moses 5.66 — PDS document references, To-Do schedule, PO tracking and delivery visibility

Apply over **Moses 5.65** on the same `main` working tree. Small incremental source-only patch; no business data is bundled or mutated during installation. Do not deploy until local regression tests pass.

## Fixes

1. **Separate customer PO from supplier PO:** Creating a supplier `PO-000xx` no longer overwrites the PDS job's customer PO field. Estimate/invoice generation suppresses leftover supplier-style `PO-000xx` values in the customer's PO field. Supplier POs remain associated using their verified job ID and number, and are listed on the dispatch ticket.
2. **Document editor:** Removes the repeated linked-job correction banner. The existing document must still be reviewed and saved to rebuild the numbered PDF before email approval.
3. **Alternate uploader:** The existing five options open a foreground upload editor over the ticket, preserving the ticket below. The existing image/PDF extraction flows for receipt and packing slip remain available and include a visible read-with-Moses action; the estimate/invoice/PO imports reuse the existing document import mechanism.
4. **PO status:** Direct quick status, tracking number, and arrival-date controls on the PO detail ticket, using existing secured persistence and status workflow.
5. **To-Do calendar:** Compact, horizontally scrollable seven-day assigned-visit strip with times, job details, and click-through View Job. Existing To-Do lists remain beneath the calendar.
6. **Email history:** A small expandable read-only Email History section on saved PDS estimate/invoice/PO cards and the PO ticket. It shows recipient, subject, timestamps, attachment, Resend message ID, and the latest signature-verified delivery event when present. The existing email button and send approval dialogs remain unchanged. Provider acceptance is never represented as confirmed inbox receipt.
7. **PO email history:** Available for review even if the PO-sending feature flag is off; the send/approve actions remain restricted by the flag and role.

## Source QA

- Reconstructed 5.65 source: **960 passed, 2 skipped** (`python -m pytest -q tests/`).
- `node --check static/app.js`, `node --check static/doorks_shared_ticket.js`, `python -m compileall -q main.py app`, and `git diff --check`: pass.
- Does **not** verify actual Resend delivery or an end-to-end browser run.

## Resend delivery verification

`state=sent` on the application ledger means Resend accepted the send request. It does **not** prove receipt by Outlook. For RE00097, look up the original email using the recipient or Resend message ID in Resend's Emails dashboard. Check the delivery/bounce/suppression record and Microsoft 365 quarantine/message trace if applicable. Do not retry an uncertain send until reconciled. Resend webhook events need to be configured with the existing signed receiver at `/doorks-assistant/public/resend/webhook`; absence of events is `unconfirmed`, not `delivered`.

## Manual browser acceptance

1. Open a known PDS job with a customer PO number, add a supplier PO, save and confirm the job customer PO remains unchanged while the supplier PO appears on the ticket.
2. Open the estimate editor. Confirm the customer PO is not a supplier `PO-000xx` and the linked-job correction banner does not appear.
3. From the job ticket open Alternate -> Receipt / Packing Slip; choose an image and click Read with Moses. Confirm extraction requires human review and the uploader is in front of the ticket.
4. Open a PO and change status/tracking/arrival date; verify the saved record after refresh.
5. Open To-Do List and check the upcoming seven-day schedule including times.
6. Expand Email History for RE00097 and confirm the status is correctly labeled **Accepted by Resend** or **Unconfirmed**, not **Delivered** without a signed delivery event. Review the provider ID in Resend.

## Deployment

Apply the patch with `git apply --check` before `git apply`; run full tests; stage only the files listed in `stage_paths.txt`. Do not stage `.venv` or `data/`.
