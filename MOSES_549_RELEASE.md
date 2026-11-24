# Doorks / Moses 5.49 — cumulative business workflow release

**Baseline:** `Doorks-PDS/Dispatch-System` commit `82745985` (Moses 5.46). This ZIP includes the unpublished 5.47 and 5.48 changes plus the 5.49 integrations. Do not install 5.47 or 5.48 separately.

**Source only:** No production records, database files, secrets or customer attachments are included. No GitHub or Render changes have been made by ChatGPT.

## Changes

- Moses AI intake: editable extracted details and saved-customer suggestion workflow from 5.47.
- Alternate Upload: QuickBooks or other externally issued estimate, invoice or PO retains the original number, job number and uploaded file. Appears on the PDS job ticket, in the matching saved document category, and remains visible in the Business Document Library. Clearly labeled **External**; no duplicate RE, JS or PO numbering, posting or receiving.
- Calendar: month cells show as many complete job rows as fit; existing day detail remains available.
- Calendar attachment intake: capped file size and read-only storage diagnostics from 5.48.
- PDS roles: Techs create/edit estimates, prepare estimate email approvals and upload estimate references; leads create/edit estimates, invoices, POs and corresponding document references; office and office admins retain broader authority. PO receiving, suppliers, payments and bulk imports remain office-controlled. Server endpoints enforce roles; showing a UI button is not authorization.
- PDS purchase orders: **Created by employee** and creation time are set from the authenticated user and cannot be changed through a PO edit. **Updated by** tracks the last editor. Historical POs without creator metadata remain untouched and show as legacy/no creator.
- Purchase-order authorizations: office/lead can prepare POs; tech cannot; office-admin-only deletion remains guarded by receiving history.
- Documents from QuickBooks are reference files until explicitly reconciled; this release does **not** import QuickBooks accounting transactions, automatically post expenses, reconcile payment, or receive stock.

## Local preflight (do not skip)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-549-check
unzip -o ~/Downloads/Doorks_Moses_549_Integrated_Office_Roles_QB_PO.zip scripts/check_moses_549.py scripts/moses_549_manifest.json -d /tmp/doorks-549-check
python3 /tmp/doorks-549-check/scripts/check_moses_549.py --root "$PWD" --phase before
```

**STOP if this fails.** It means your Mac has newer/different source files and needs a merge, not forced overwriting.

## Install and test

```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_549_Integrated_Office_Roles_QB_PO.zip -d .
python3 scripts/check_moses_549.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_identity_review.js
git diff --check
```

Local reconstructed 5.49 suite: **921 passed, 2 skipped**, using Python 3.13; your Mac environment may differ. Do not push on a test failure.

## Commit and push (YOU do this, when ready for Render auto-deploy)

```bash
cd ~/doorks-deploy-edit
# See the exact staging block in the assistant message. Do not stage data/, .venv/, backups or test records.
git diff --cached --check
git diff --cached --stat
git commit -m "Doorks Moses 5.49 - QB references, role permissions and PO creator tracking"
git push origin main
```

## Office acceptance in a safe test job

1. Confirm existing jobs, estimates/invoices, PO numbers and data were preserved.
2. Create a test PO as a lead: confirm **Created by** is the signed-in lead and the date is present. Edit as office staff and confirm **Created by** remains unchanged while **Updated by** changes.
3. Confirm a technician cannot create a PO/invoice, but can create/edit an estimate and prepare its email approval (do not approve until ready).
4. Upload a QuickBooks estimate, invoice, and PO with their original numbers and a test job reference. Check the job ticket, their saved lists and Business Document Library. Do not confuse them with PDS-issued documents or receiving events.
5. Run the purchasing flow with a disposable test PO: create → receive → packing slip → supplier bill → payment tracking, checking the existing Accounting Hub after each step. No real supplier payment should be initiated in test.
6. Verify calendar density, month/day expansion, original attachments and upload-size error handling.
7. Verify Moses read-only job lookup, separate estimate scopes, van stock, and an unsent approval. Live Agents SDK remains separately testable.

## Moses, Twilio, Resend — activation and verification

**Render environment (user-controlled):**
- `OPENAI_API_KEY` (existing key; do not paste into chat)
- `DOORKS_MOSES_PDS_AGENT_ENABLED=true`
- `DOORKS_MOSES_WEB_SEARCH_ENABLED=true` to enable optional hosted web search
- Other agent configurations still require a real authenticated live conversation test. Enabling a flag is not proof Moses's tools work end to end.

**Twilio:** Confirm the public `/pds/sms`, `/pds/sms/privacy`, `/pds/sms/terms` links; finish A2P 10DLC approval before live customer texts. Verify `PDS_SMS_PUBLIC_BASE_URL`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, the registered sender/messaging service, and signed webhook URLs. Test consent and STOP on a controlled phone before enabling bulk/customer alerts.

**Resend:** Confirm your verified sending domain, configured sender, document-specific Reply-To addresses, and `MOSES_PDS_DOCUMENT_SEND_ENABLED` only for an approved controlled test. Verify provider acceptance **and** signed delivery receipts; ambiguous outcomes require manual review.

**These are live provider verification gates, not guarantees of production readiness from offline tests.**
