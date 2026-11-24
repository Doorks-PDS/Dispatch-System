# Doorks / Moses 5.55 — Supplier Pricing Queue + PDS Workspace + Sidebar Badges

**Base:** Your installed **5.54** source, including the 5.53 supplier-quote functionality. This patch also includes the **legacy Alternate-label test correction** that you have not yet applied. You do **not** need to run the previous correction commands or reinstall 5.54.

## Included

- **Moses Job Flow:** Tabs for Quotes, Supplier Pricing, and Invoices. Staff can select **Request Supplier Quote** from an eligible job; it moves to the supplier-pricing lane **visually** while its RFQ is active. The underlying job record, status, invoices, and estimates are not changed merely because a request was created. When the RFQ is marked Ready for Estimate the job reappears in its normal work queue.
- **RFQ editor:** Select an existing supplier, associate a job #, quantity, items/dimensions/specifications and an optional message/subject. Attach up to **8** PDFs or PNG/JPEG/WebP images (4 MB each, 12 MB combined). Files and staff-attributed status history use the existing PDS data directory. No automatic inventory, price, or accounting change.
- **Email:** Save draft → **Review Email & Send**. A concise preview shows From, To, Reply-To, Subject, message and attached files. **Approve & Send via Resend** requires a direct human confirmation. The email payload includes the verified saved attachments. An intent is saved before contacting Resend; uncertain provider outcomes are held and must not be blindly resent.
- **Supplier response:** Track Awaiting Supplier → Quote Received → Ready for Estimate. Manually record supplier quote number, unit cost, lead time, reply PDF and photos on the same request. Supplier replies go to the configured Reply-To inbox; **automatic inbound email matching/parsing is not part of this patch**.
- **PDS workspace initialization:** A successful login and PIN login explicitly set the server session to PDS. The existing `/platforms/current` endpoint also reconciles missing/legacy PDS session values without overwriting an admin's valid Doorks or SDC selection. The UI waits for workspace initialization before running PDS calendar and badge requests. This addresses the visible-PDS-but-session-not-PDS problem.
- **Sidebar notification badges:** All PDS navigation buttons with subtitles reserve a stable two-line title/subtitle layout. Notification counts are positioned separately, rather than pushing small subtitles sideways. Includes the Fleet Hub example.
- **Legacy test correction:** The stale test assertion for `Alternate Upload` is replaced by `Alternate`; the actual application label stays unchanged.

## Safety / scope

No production database, customer documents, images, secrets, credentials, backup folders or Render configuration included. **Source tests are not live deployment certification.** Resend delivery, supplier inbox response, persistent Render disk mounting, file upload/download, Safari responsive layout, employee workspace sign-in, and final estimate handoff need authenticated live acceptance testing. In particular, Resend provider acceptance is not proof of supplier inbox delivery.

## Installation (Mac)

First obtain `Doorks_Moses_555_Supplier_Queue_PDS_Fixes.zip` in Downloads. In `~/doorks-deploy-edit`:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-555-check
unzip -o ~/Downloads/Doorks_Moses_555_Supplier_Queue_PDS_Fixes.zip \
  'scripts/check_moses_555.py' 'scripts/moses_555_manifest.json' \
  -d /tmp/doorks-555-check
python3 /tmp/doorks-555-check/scripts/check_moses_555.py \
  --root "$PWD" --phase before
```

**STOP if the before checker does not PASS.** Then:

```bash
unzip -o ~/Downloads/Doorks_Moses_555_Supplier_Queue_PDS_Fixes.zip -d .
python3 scripts/check_moses_555.py --root "$PWD" --phase after
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Commit only after verification and local acceptance

This set includes all 5.55 files. If you still have uncommitted 5.54 changes, stage those as well, but always inspect `git diff --cached --stat` / `git status --short` first. Do not stage `data/` or `.venv/`.

```bash
git add static/app.js static/style.css \
  app/routers/auth.py app/routers/platforms.py app/routers/pds_supplier_quotes.py \
  app/services/moses_email_transport.py \
  tests/test_moses_38_interface.py tests/test_moses_45_direct_workflows.py \
  tests/test_moses_47_queue.py tests/test_moses_549_qb_roles_po_creator.py \
  tests/test_moses_554_job_flow_calendar.py tests/test_moses_555_supplier_pricing_flow.py \
  tests/test_moses_555_workspace_session_and_badges.py \
  MOSES_554_RELEASE.md MOSES_555_RELEASE.md \
  scripts/check_moses_554.py scripts/moses_554_manifest.json \
  scripts/check_moses_555.py scripts/moses_555_manifest.json

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.55 - supplier pricing queue and PDS workspace fixes"
git push origin main
```

If local `main` is behind remote `main`, reconcile before pushing; never force push.

## Acceptance checklist

1. After login directly into PDS, open the technician Scheduler: staff should load without switching workspaces. Switch to SDC and back as admin, and confirm both boundaries still apply.
2. Confirm badges on Fleet Hub, To-Do, Job Flow, Parts List and Time Off never displace each subtitle at desktop and tablet widths.
3. In Moses Job Flow, click **Request Supplier Quote** on a disposable test job. Save a draft with supplier, specs and two small files. Confirm the job sits in Supplier Pricing pending review and that download/open works for both files.
4. Review the exact supplier recipient/message/attachments before sending. **Do not use a real supplier on first test**. If enabled, send a test to your own controlled inbox; inspect Resend logs. Repeated click must not resend.
5. Attach a test reply PDF to the RFQ, enter quote number/cost/lead time, mark Ready for Estimate, and confirm the job returns to Quotes and no parts were silently added to inventory.
6. Re-test recommendation thumbnails, invoice creation from linked quote, time-off calendar grouping and the document status-on-send behavior from 5.54.
