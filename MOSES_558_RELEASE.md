# Doorks / Moses 5.58 — Resend Readiness & Cleaner Customer Notifications

**Base:** Moses 5.57 source on `main`. Small incremental patch. No customer records, databases, credentials, attachments or saved business documents are included.

## Changes

- **Supplier quote email review:** Compact From / To / Reply-To / Subject, scroll-contained message, existing saved attachments and clear, sticky actions. A read-only server configuration check identifies missing setup without disclosing the Resend key. **Approve & Send** is disabled until the sender, recipient, Reply-To, provider and key prerequisites are valid. Sending remains approval-gated, and Resend provider acceptance does **not** mean inbox delivery.
- **PDS customer notification on dispatch ticket:** Cleaner collapsed composer with Method, Type, saved recipient, Subject and Message. Shows sender and Reply-To when configured and blocks disabled email approval paths *before* creating a proposal. Prepared requests appear as compact review cards with **Approve & Send** / **Discard**. History is collapsed and each entry can expand for details. Email and text still use their existing independent approval endpoints. Nothing is sent on schedule save or page load.
- **Email readiness endpoint:** Read-only authenticated `/pds-schedule-notifications/email/readiness`, returning only readiness, sender, Reply-To and non-secret setup issues. Does not call Resend or mutate settings. Existing backend send restrictions, provider uncertainty holds, and customer recipient validation remain unchanged.
- **Mobile:** Single-column notification composer on narrow screens.
- **Tests:** New regression tests for environment gating, no secret exposure, approval controls and the compact UI; updates one older fleet test expecting the removed `Use saved:` button.

## Required Render environment setup (not bundled in the patch)

Configure the **existing PDS/Doorks Render service**. Do not post an API key in chat or commit it to Git.

| Environment variable | Value |
|---|---|
| `MOSES_EMAIL_PROVIDER` | `resend` |
| `MOSES_DOCUMENTS_FROM` | `NoReply@prioritydoors.com` |
| `RESEND_API_KEY` | Your actual active Resend API key, stored as a Render secret |
| `PDS_SUPPLIER_QUOTES_REPLY_TO` | `reception@prioritydoors.com` |
| `PDS_GENERAL_REPLY_TO` | `reception@prioritydoors.com` |
| `MOSES_ESTIMATES_REPLY_TO` | `Estimates@prioritydoors.com` |
| `MOSES_INVOICES_REPLY_TO` | `Invoice@prioritydoors.com` |
| `MOSES_PDS_ESTIMATES_REPLY_TO` | `Estimates@prioritydoors.com` |
| `MOSES_PDS_INVOICES_REPLY_TO` | `Invoice@prioritydoors.com` |
| `MOSES_PDS_DISPATCH_REPLY_TO` | `reception@prioritydoors.com` |

For customer dispatch schedule emails, keep `PDS_SCHEDULE_EMAIL_SEND_ENABLED` **unset/false** until the domain/key, actual company mailboxes, recipient verification and test delivery to an inbox you control are confirmed. Only then explicitly enable with `PDS_SCHEDULE_EMAIL_SEND_ENABLED=true`. This is an external customer-sending gate; the patch does not enable it.

Resend domain must be verified and `NoReply@prioritydoors.com` an authorized From identity for your Resend account. Reply-To addresses must actually receive mail. SMS/Twilio permissions and consent remain separate. No live email send, DNS check, or Render environment mutation was performed when building this patch.

## Installation (Mac)

First ensure the ZIP is in `~/Downloads` and you are on **Moses 5.57** main:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-558
unzip -o ~/Downloads/Doorks_Moses_558_Resend_Notifications.zip -d /tmp/doorks-558
git apply --check /tmp/doorks-558/moses_558.patch
```

Only if the check passes (no output means PASS):

```bash
git apply /tmp/doorks-558/moses_558.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

Do not apply if the compatibility check fails. Avoid `git add .`, force pushes, new branches and additional Render services.

## Stage / commit / deploy

After local acceptance:

```bash
git add static/app.js static/style.css \
  app/routers/pds_supplier_quotes.py app/routers/pds_schedule_notifications.py \
  app/services/pds_schedule_notifications.py \
  tests/test_pds_vehicle_flow_544.py \
  tests/test_moses_558_email_setup_and_notification_ui.py \
  MOSES_558_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.58 - Resend readiness and compact notifications"
git push origin main
```

## Live acceptance

1. Confirm source 5.58 is deployed and Resend settings are populated on the correct service.
2. Supplier Pricing > test RFQ > Review Email & Send: From shows `NoReply@prioritydoors.com`, To is the verified test supplier, Reply-To is reception, subject/body/files are correct. Only manually approve a request to a controlled test inbox; check Resend logs and inbox separately.
3. Dispatch ticket > Notify Customer: before enabling schedule emails, show a concise disabled message and no send action. After explicit enabling/testing, prepare a test email, verify the saved recipient and content, approve once, and check provider acceptance and recorded history.
4. Verify no duplicate SMS/email, no unauthorized recipients, and no changes to job status, schedule or inventory caused merely by previewing/preparing a notification.
5. Check phone/tablet width and confirm the notification form collapses to one column.

**Source tests are not live provider certification.**
