# Moses 5.60 — PDS Dispatch Email Gate, Supplier RFQ Copy, Payroll PIN

**Base:** Moses 5.59 on `main` (commit `558c56bd4eab741adb6a4c250e121146a460e733`). The 5.58 Resend/notification and 5.59 agent/web updates are retained; this is an incremental patch, not a replacement deployment.

## Fixes

- **Dispatch email:** Confirmed that `PDS_SCHEDULE_EMAIL_SEND_ENABLED` is an independent runtime permission. The Resend sender, reply-to, approval and recipient-verification logic remain unchanged. This flag was set to `true` on the connected Render `Dispatch-System` service after a successful supplier-quote email test; Render automatically started rebuilding 5.59 to take effect. **The flag does not send any email by itself.** Staff must still review and explicitly approve the saved-job recipient and message. Do not enable Twilio SMS (`PDS_SMS_SEND_ENABLED` stays `false` while A2P is under review).
- **Supplier quote emails:** Remove automatic internal `Job: ...` and `1 × ...` from outgoing supplier emails and preview, including the default subject. Quantities are supplied naturally in Description, which stays editable. Job linkage and original quantity remain in saved RFQ metadata and the Job Flow queue. Previously saved drafts use the cleaned presentation when previewed/sent; sent historical messages are not altered. Supplier attachments, original reply-to, explicit send approvals and uncertain-send safeguards are unchanged.
- **Payroll PIN:** Fix the navigation click-event bug where a truthy event object bypassed the PIN prompt. Require literal `true` for the server-confirmed continuation; always prompt on entry to Payroll even if Roll-Up Data was previously unlocked. The server already validates `PDS_OFFICE_REPORT_PIN` (default `2005`) with timing-safe comparison and throttles wrong attempts. Do not store the PIN in JS. This is a *UI-entry lock plus existing role-based controls*; separate backend data-access hardening may still be required for any payroll datasets exposed by generic timecard APIs.

## Installation (Mac)

Install **over your current 5.59**, not 5.58 or 5.57. Back up or commit unrelated pending local changes first. If the preflight fails, stop and do not use `--reject` or `--3way` blindly.

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-560
unzip -o ~/Downloads/Doorks_Moses_560_Dispatch_Supplier_Payroll.zip -d /tmp/doorks-560
git apply --check /tmp/doorks-560/moses_560.patch
# Only if there are no errors:
git apply /tmp/doorks-560/moses_560.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

Run the full tests on your own Mac, as production Python versions and installed dependencies can differ. The patch source tests passed: **988 passed, 2 skipped**.

```bash
# Inspect staging; only four paths should be present.
git add static/app.js app/routers/pds_supplier_quotes.py \
  tests/test_moses_552_office_import_pin.py \
  tests/test_moses_560_dispatch_supplier_payroll.py MOSES_560_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.60 - supplier RFQ email and payroll PIN guard"
git push origin main
```

## Live acceptance

1. Confirm the Render 5.59 environment change reached **Live**; refresh Safari and open a *test job with the user's own saved email*. Review appointment notification, approve once, then confirm provider accepted it and it arrived in the test inbox. Do not send unsolicited customer messages.
2. Preview a **new** supplier request: subject does not expose internal job #, text does not inject `1 ×` or `Job:`, but the RFQ still links to the job internally and its files remain attached. Do not resend a previously sent request.
3. Click **Payroll** while logged in with the appropriate office role: masked PIN must appear and reject a wrong PIN; `2005` must unlock. Navigate elsewhere and return: PIN must be requested again even after a Roll-Up unlock.
4. Twilio campaign is still pending; keep SMS sending disabled until carrier approval and opted-in real-device verification.
5. Moses web-search success remains **unverified live**; do not conflate source-level agent configuration with a real hosted web-search call. Follow up separately for the live web probe.

**No automatic customer email, SMS, quote, or payroll change is performed by installing this patch.**
