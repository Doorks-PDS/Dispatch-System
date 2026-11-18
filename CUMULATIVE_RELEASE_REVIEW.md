# Doorks / Moses 5.17 — cumulative integration candidate (November 18, 2026)

## Baseline
Patch is relative to the user-supplied `doorks-deploy-edit(6).zip` snapshot. Apply only after checking your current working copy has not diverged; no separate branch or Render service. All previously integrated Twilio A2P and dispatch UI corrections are included. No production data or credentials are shipped.

## Implemented in this candidate
- PDS A2P informational signup, Privacy Policy, and Terms pages (`/pds/sms`, `/pds/sms/privacy`, `/pds/sms/terms`). The URLs must actually be published and checked before Twilio registration submission.
- HMAC-signed inbound Twilio SMS callback (`START`/`YES` double opt-in, `STOP`, `HELP`) with durable, idempotent SQLite consent ledger.
- Moses PDS office-admin SMS approval flow, including validated matching job phone, confirmed SMS consent, human decision, write-ahead `needs_review` intent before external API call, no auto-retries for uncertain outcomes, Twilio delivery callbacks, and receipt retrieval.
- Moses PDS quote readiness summaries, server-backed invoice handoff *review packets* (deduplicated by exact job snapshot), and PDS operations overview and receipts. These are **not** official invoices, customer sends, prices, payments, or bookkeeping entries.
- Moses agent can prepare/read SMS approvals and read verified invoice handoffs and operations review. SMS approval review cards added to existing Action Center; sends require office admin and a further confirmation.
- Moses launcher hidden on unauthenticated login; redundant Saved Customer Locations selector removed from New Dispatch; desktop customer suggestions improved.
- PRIO Coin protected **design preview only**, no investments, ledger, benefits, payroll, or allocation changes.
- Previous PDS, SDC, Atlas, documents, purchasing and Resend modules preserved from source snapshot.

## Automated local validation
- `python -m pytest -q tests/ --disable-warnings`: **800 passed, 2 skipped**, 4 warnings.
- `node --check static/app.js` and `node --check static/moses_action_center.js`: pass.
- `python -m compileall -q main.py app`: pass.

## Must be resolved BEFORE production deployment
- Real Render durable mount, data retention and restore test for both PDS existing data and the `pds_sms` and `moses_pds` SQLite ledgers.
- A2P registration approved, Twilio sending number registered and verified; public opt-in instructions and policies accessible and consistent; inbound and delivery callbacks correctly configured and tested with real phones. Ensure Twilio Advanced Opt-Out/STOP synchronization: carrier-provider decisions remain authoritative.
- Set `PDS_SMS_SEND_ENABLED=true` **only after** A2P approval, provider verification, durable disk and end-to-end STOP/YES/revocation tests. Until then it defaults to disabled.
- Complete signed inbound and delivery provider checks, and verify failure/ambiguity recovery with Twilio Console logs. SMS API success means **submitted**, not delivered.
- Run authenticated live OpenAI Agents SDK tool call and Moses PDS/Doorks/SDC workspace isolation tests; validate human approval and audit receipts.
- Verify Resend document emails and signed webhooks with the intended workspace-specific reply-to addresses.
- Verify Stripe **sandbox** checkout and webhook, before enabling financial capabilities or accepting production charges.
- Browser smoke test permissions, quote/invoice handoff, customer autocomplete and scheduling across desktop/tablet/phone; review an actual saved job with PDS office admin.
- The original unpublished Moses 5.17 installer source was not accessible. This implements functionally scoped replacement modules and tests, **not** a verified byte-for-byte restoration of that earlier installer. Full release gate and actual production integration cannot be certified in this offline development environment.
- PRIO Coin preview remains non-operational, pending a separate reviewed legal, tax, financial, and durable persistence implementation.

## Render environment keys (do not put values into Git)
- `PDS_SMS_PUBLIC_BASE_URL=https://<real Doorks host>` (HTTPS origin without trailing slash)
- `PDS_TWILIO_NUMBER=<the registered Twilio E.164 number>`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (secret)
- `PDS_SMS_SEND_ENABLED=false` until approved and tested
- `DOORKS_DATA_DIR=<durable mounted directory>` consistent with your existing storage setup
- Twilio incoming SMS webhook: `POST <PUBLIC_BASE_URL>/pds/sms/twilio/inbound`
- Twilio send delivery callback auto-included on approved SMS: `POST <PUBLIC_BASE_URL>/pds/sms/twilio/status`
- Confirm Twilio's Advanced Opt-Out setup rather than assuming its STOP processing is delivered to the app.

## Safe local install commands — when ready to review
```
cd ~/doorks-deploy-edit
git status --short
# Backup your current checkout before applying; compare files against the snapshot.
unzip -o ~/Downloads/Doorks_Moses_517_Cumulative_Integration_Candidate.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
node --check static/app.js
node --check static/moses_action_center.js
python3 -m compileall -q main.py app
git diff --stat
# ONLY AFTER completing the listed live checks and approving the final diff:
git add main.py requirements.txt static/app.js static/moses_action_center.js app/routers/pds_sms.py app/routers/moses_action_center.py app/routers/moses_pds_sms.py app/services/pds_sms_consent.py app/services/moses_agent.py app/services/moses_pds_twilio.py app/services/moses_pds_invoice_plan.py app/services/moses_pds_operations_plan.py app/services/moses_pds_quote_plan.py app/services/moses_pds_workflow.py app/resources/prio_coin_admin_preview.html tests/
git commit -m "Doorks cumulative Moses 5.17 and PDS SMS integration"
git push origin main
```
These Git commands are instructions only. No push/deploy is performed or authorized by this document.

## November 18 follow-on: PDS Van Stock (cumulative, not separate)
- **Forms → Van Stock** appears immediately under **Time Off Request**. A badge counts van shortages plus warehouse shortages. Parts List navigation also shows warehouse shortages.
- One van setup per actual technician/lead, created manually from the existing PDS employee records. **No van is pre-created for Erick or anyone else.**
- A company standard van-stock template can add catalog parts with per-part optional minimum and target. When a template changes, it adds missing van parts but does not overwrite a technician's customized values.
- A van can include extra parts, with overrides for its minimum and target.
- Stock ledger supports verified warehouse-to-van transfers, returns, job usage, and separately audited physical van counts (including zero). Only transfers/returns adjust warehouse stock balances; existing original warehouse movements are preserved. Physical counts explicitly **do not deduct** warehouse inventory; reconcile the initial count against warehouse inventory to avoid double-counting legacy stock.
- Stock IDs are existing PDS Parts List IDs; no parallel part catalog or automatic purchasing. Warehouse and van alert thresholds are optional; unconfigured thresholds generate no alert, including at zero. Warehouse alerts require a stock-recorded balance (unknown quantities are not silently set to zero).
- All writes require logged-in PDS office role, existing PDS workspace, cross-worker inventory lock and append-only audit movements with request-id dedupe. Technicians can inspect but cannot edit stock counts.
- Existing part deletion is blocked while a part is linked to van stock or its movements.
- Van stock data is persisted at `DOORKS_DATA_DIR/pds_van_stock.json`; this must be on the **existing verified Render persistent disk**, never a new ephemeral mount.
- Added optional `min_stock` to existing parts catalog records and display in the Parts List; old blank thresholds remain disabled.
- Tests: `806 passed, 2 skipped` (full local suite) and successful Python+JS compilation/syntax tests.

### Operational setup after verified release
1. Review the **actual** PDS technician list and create vans only for the techs/leads who have one. Erick has no van by default.
2. Pick core parts from the existing Parts List for the standard van template and set target and alert minimum. Override per van only if needed.
3. Conduct physical stocktakes. Before recording initial van counts, confirm whether historical warehouse counts already included van items; reconcile totals with stock adjustment audit to avoid double-counting.
4. Test a controlled warehouse→van transfer and low-stock alert on a noncritical item; confirm return and job usage history.
5. Review warehouse low-stock badges and manual purchasing recommendations. This change does **not** automatically draft/send POs or supplier notifications.

### Additional limitations
- No production deployment, Render configuration change, financial transaction, SMS, or customer message was initiated from this package.
- Render connector access requires choosing a specific Render workspace before read-only environment inspection; that selection has not been provided in this session. Live disks, secrets, Twilio A2P approval, OpenAI/Resend/Stripe delivery and webhooks are still unverified.
- `PDS_SMS_SEND_ENABLED` must remain disabled until the live gating checks listed above pass. The PRIO Coin preview is still a prototype.

## November 18 follow-on: PRIO Coin navigation (5.20)
- PDS **Office Flow → PRIO Coin** is visible only to authenticated `office_admin` users in the PDS workspace.
- Opens the existing protected `/pds/prio-coin-preview` in a separate tab. The route also enforces admin and workspace authorization server-side.
- **Preview only**: no benefits plan, employee allocations, payroll, ledger transactions or investments are enabled.
- No production changes, Github push, Render calls, or deployment.
- Local tests: 807 passed, 2 skipped; JavaScript syntax passed.

## Moses 5.21 follow-on — multiple completion forms / separate estimate scopes
- Read-only PDS office/lead endpoint `GET /moses-action-center/pds/jobs/{job_id}/estimate-scopes` examines the actual saved `CalendarStore` job by exact internal ID.
- Each form containing recommendation/parts/labor scope is presented as a **separate proposed estimate scope**, preserving the saved form ID/index and door location for review. Missing quote readiness is flagged; it is never silently upgraded to approved.
- A single form explicitly asking for separate/multiple quotes is marked `needs_manual_split` rather than automatically split, priced, numbered, emailed, or linked to an estimate. The existing estimator and approval process remains authoritative.
- This is the source-backed scoping foundation. Manual scope editing and fully separate durable draft/estimate handoff are still pending and require validation with real PDS examples.
- Additional test suite: 814 passed, 2 skipped; Python/JS compilation successful.

## Moses 5.22 follow-on — editable separate estimate review drafts
- Existing PDS Moses Drafts ledger (`moses_pds/quote_review_drafts.json`) is reused; no competing draft store, extra service, database, or calendar mutation.
- `POST /moses-drafts/prepare-job-scopes` accepts explicit office-reviewed scope title/description and the exact completion-form index; it verifies active PDS workspace, permissions, existing job, quote status, quote readiness, and that each form contains a saved recommendation.
- A single form can produce multiple **separate unpriced review drafts**, and multiple forms can also produce distinct drafts. Every draft has source form ID/index/digest, is fingerprinted for dedupe, and is still subject to the existing Moses Drafts review, parts/freight, approval and handoff gates.
- In the Moses Action Center PDS job-follow-up card, **Separate estimate scopes** opens an editable per-form review panel. Office staff can remove or add rows for a form, edit location/title and scope, and explicitly save separate review drafts.
- No estimate number, price, official document, sent email, or job status is changed; this is a multi-scope *review* bridge, not automatic estimate issuance. Existing single-job draft preparation remains available for backwards compatibility.
- **Known limitation / gate:** The existing estimator still needs a verified, separate actual-document linkage and issuance process for each approved scope. Current `sent_quote_number` job-level validation blocks preparing/approving additional scopes after a first estimate has already been sent. Do not represent this as multiple automatically issued estimates; that handoff requires separate production-editor integration and end-to-end browser tests.
- Tests: `819 passed, 2 skipped`, Python compile and JS syntax checked. All live external-provider and data-persistence checks above remain pending. **Do not deploy this candidate until the release gates are approved by the user.**

## Local install/push procedure for 5.22 (ONLY once approved)
```
cd ~/doorks-deploy-edit
# Verify your working tree matches the supplied baseline before applying.
git status --short
unzip -o ~/Downloads/Doorks_Moses_522_Cumulative_Editable_Scope_Drafts_Review.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
node --check static/app.js
node --check static/moses_action_center.js
python3 -m compileall -q main.py app
git diff --stat
# Only when user chooses a deployment window AND confirms the verified diff:
git add main.py requirements.txt static/app.js static/moses_action_center.js app/routers app/services app/resources tests
# After reviewing git diff and ensuring only approved files are staged:
git commit -m "Doorks cumulative Moses 5.22 review draft scoping"
git push origin main
```
No commits, pushes, deployments or live Render operations were performed during packaging.

## Moses 5.23 follow-on — PDS Scheduler customer notifications (cumulative)
- A compact **Notify Customer** expander now appears inside the existing PDS Scheduler on office job tickets, with **Email / Text / Email & Text**, appointment confirmation, schedule change, ETA and custom message choices. It pre-fills recipients from the saved ticket and provides a modifiable plain-text preview.
- Preparing a message does **not** update the schedule or send anything. Each method creates a distinct persisted proposal and shows explicit **Approve & send** / **Reject** controls. The server requires PDS `office_admin` for both creation and decisions; editing recipients does not bypass matching the exact saved job contacts.
- Text uses the existing Moses 5.17 Twilio consent-checking approval service and is blocked without opted-in consent. Email uses a new minimal PDS schedule-notification approval ledger and the existing Resend transport, requiring `PDS_SCHEDULE_EMAIL_SEND_ENABLED=true`, `MOSES_EMAIL_PROVIDER=resend`, `MOSES_DOCUMENTS_FROM`, `RESEND_API_KEY`. The send path checks the recipient again immediately before approval, persists an irreversible `needs_review` state before contacting Resend, and does **not** automatically retry uncertain outcomes.
- Sending is always user-initiated and explicitly confirmed. Any provider acknowledgment is marked **submitted**, never delivered. A **Notification History** button lets PDS office administrators inspect the saved email and SMS proposals and outcomes for that exact job. No customer or job records are changed by preparing messages.
- Text messaging is independently disabled unless `PDS_SMS_SEND_ENABLED=true` and valid Twilio settings/real A2P consent are configured. A combination Email & Text may prepare one method while the other fails verification; the UI shows each result, never claims both succeeded.
- New backend routes: `POST /pds-schedule-notifications/email/proposals`, `POST /pds-schedule-notifications/email/proposals/{id}/decision`, `GET /pds-schedule-notifications/jobs/{job_id}/email-history` and `GET /moses-action-center/pds/sms/jobs/{job_id}/history`.
- **Before deployment**: live browser verification of the ticket UI, sender-domain/Reply-To settings, Twilio A2P proof/approval and STOP/YES handling, signed delivery callbacks, persistent directory, and real provider acceptance. Schedule change and ETA wording is not auto-generated from GPS or actual technician travel. Outbound flags should remain off until tested; no messages were sent by these tests.
- Local source regression: **824 passed, 2 skipped**, plus Python compilation, JS syntax and cumulative archive comparison; no Render/GitHub mutations.

## Local patch installation — 5.23, only when user approves a deployment window
```
cd ~/doorks-deploy-edit
git status --short
# Download Doorks_Moses_523_Cumulative_Scheduler_Notifications_Review.zip before executing:
unzip -o ~/Downloads/Doorks_Moses_523_Cumulative_Scheduler_Notifications_Review.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
node --check static/app.js
node --check static/moses_action_center.js
python3 -m compileall -q main.py app
git diff --stat
# Review every staged file before committing:
git add main.py requirements.txt static/app.js static/moses_action_center.js app/routers app/services app/resources tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
# Only after all live verifications and explicit user approval:
git commit -m "Doorks Moses 5.23 cumulative Scheduler notifications"
git push origin main
```
The above commands are **not** authorization to deploy. The updated package is a source candidate only.

## Moses 5.24 follow-on — explicit saved estimate linkage for separate scopes
- For an **approved separately identified Moses scope**, PDS office admin can associate **one already-saved official RE estimate** to that scope. The association is durable in the existing `moses_pds/quote_review_drafts.json` ledger, with actor/timestamp, version checking, audit event and no alternative data store.
- Strict matching requires same exact job ID (or unique validated legacy job number), customer, estimate type, saved source form ID/index and unchanged source-form digest. One saved official estimate cannot be associated to two Moses scopes, and an already linked scope cannot silently switch documents. An existing linked number can be re-confirmed without another write.
- The Moses Drafts **Email / Delivery** screen shows verified saved estimate candidates and requires explicit **Link to this scope** confirmation before offering the per-scope document for approval. After linking, unrelated estimates from that job are not offered through this scope's delivery list. It still uses the independent PDS Resend proposal/approval workflow, never automatically sends.
- The estimator handoff now returns the exact completion-form index; ticket UI verifies that exact form instead of choosing the first matching legacy identifier. This avoids confusing distinct forms with the same legacy source ID.
- The existing one-job `sent_quote_number` stays intact and is **not overwritten**. Linking another approved scope remains possible after the first sent-estimate status update, but preparing *new* multi-scope drafts after a job is already Quote Sent remains blocked pending verified policy/editor workflow. **This revision does not automatically issue any estimate or make the existing editor multi-document-aware.**
- Automated tests: `831 passed, 2 skipped`; Python compilation and JavaScript syntax passed. No live provider testing or real browser session was performed.
- **Still not production-ready**: inspect real PDS job/document samples, validate editor-created PDFs and saved document IDs, verify independent Resend approvals, Twilio A2P registration and live STOP tests, Render persistence, customer-facing review, payroll/accounting safeguards and backup/restore plan. Do not deploy merely on local test count.

### Safe install procedure, when approved by the user
```
cd ~/doorks-deploy-edit
git status --short
# Confirm this checkout still matches the Nov 18 uploaded working snapshot.
# Extract the ONE final cumulative ZIP rather than stacking earlier candidates:
unzip -o ~/Downloads/Doorks_Moses_524_Cumulative_Explicit_Estimate_Links_Review.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
node --check static/app.js
node --check static/moses_drafts.js
node --check static/moses_action_center.js
python3 -m compileall -q main.py app
git diff --stat
# After diff review and live approval gates ONLY:
git add main.py requirements.txt static/app.js static/moses_drafts.js static/moses_action_center.js app/routers app/services app/resources tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.24 cumulative multi-estimate scope linkage"
git push origin main
```
No installation, commit, push, live provider action, or Render modification was performed in preparing this source review candidate.

## Moses 5.25 — predeployment integration pass, November 18
- Reviewed 5.24 changed-file package against the user-uploaded working-code copy; did **not** alter GitHub, Render, or live PDS data.
- A separate estimate-review scope can now be **prepared, independently approved, and handed off for estimator review after the job enters Quote Sent** following its first sent estimate. The exact source completion form, its digest, workspace, office permissions, and per-scope key remain required. This action neither overwrites `sent_quote_number` nor sends or creates an estimate.
- The legacy one-job quote preparation and validation remain blocked after any sent estimate. Jobs in Done/closed status are still blocked. Existing official estimate linking protections remain unchanged.
- This is not automated multi-estimate issuance: the office must still create each official RE estimate in the existing editor, explicitly link each saved document to its approved Moses scope, verify the recipient, and approve the individual send.
- Regression tests: **833 passed, 2 skipped** locally (including two added after-sent-scope cases); Python compilation and JS syntax checks passed.
- **Do not deploy based only on this result.** Remaining release gates: actual authenticated office browser flows (ticket Scheduler notification preview/approval/history; multiple form scopes → estimator → distinct RE documents → scope-specific Resend sends; van stock movements); Twilio A2P registration and verified public policy pages; signed START/YES/STOP and callback tests; Resend controlled delivery test; Stripe sandbox/test webhooks; PRIO only as labeled admin preview; durable disk backup and restore rehearsal. The existing calendar folder's approximately 9.7 GB size also deserves offline investigation, with no production data deletion.
- Prior to installation, confirm the Mac working checkout still matches the uploaded November 18 snapshot. Any new uncommitted local changes must be compared and preserved rather than overwritten. User alone installs, commits, pushes, and initiates any deployment.

### Source-only installation and review commands (not authorization to deploy)
```
cd ~/doorks-deploy-edit
 git status --short
# Make an independent local backup before unzipping. Review existing local modifications.
# Download Doorks_Moses_525_Cumulative_Deployment_Preflight.zip
unzip -o ~/Downloads/Doorks_Moses_525_Cumulative_Deployment_Preflight.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
# After manual diff inspection, ONLY when the user chooses the deployment window:
git add main.py requirements.txt static/app.js static/moses_action_center.js static/moses_drafts.js app/routers app/services app/resources tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.25 cumulative multi-estimate preflight"
git push origin main
```

## Moses 5.26 — conversational multi-estimate visibility, November 18
- Connected the **existing** PDS saved completion-form estimate-scope inspection service (`moses_pds_estimate_scopes.inspect`) to the conversational Agents SDK as `get_pds_separate_estimate_scopes`. Moses can now answer a verified job-specific question about separate quotations from original forms instead of relying on an Action Center-only view.
- Input must be the exact internal PDS job ID obtained from search. The underlying service verifies the session, PDS workspace, allowed office/lead roles, exact job match and source forms.
- Returns individual source form indices/IDs, saved recommendations and locations, explicit multi-quote flags and readiness warnings. It is **read-only**: no estimates are numbered, priced, issued, approved or sent.
- Preserved all existing PDS, Doorks and SDC agent tool boundaries; updated the tool-whitelist regression test to include only this PDS inspection tool.
- Local suite: **836 passed, 2 skipped**. Python compilation and JavaScript syntax checks passed.
- **Not yet deployment-approved**: UI/browser end-to-end checks, real Agents SDK execution with credentials, existing-calendar disk growth investigation, Twilio A2P approval and SMS callback checks, Resend delivery, Stripe test mode and persistent-data backup remain external/manual release gates. PRIO Coin remains a preview. No GitHub or Render actions performed.

## Moses 5.27 — SMS production readiness audit (November 18, 2026)
- Extended the **existing** `moses_release_gate.assess` check with static, read-only Twilio configuration observations, A2P verification blockers, and consent/receipt ledger **existence** checks. Nothing is sent or written; the check never enables SMS or authorizes deployment.
- Release diagnostics report only booleans (no Twilio SID, auth token, or sensitive configuration values). A2P approval, consent validity, live callbacks and end-to-end delivery remain explicitly unverified.
- Updated release-gate tests to enforce fail-closed behavior and no file creation. Full local regression: **839 passed, 2 skipped**; this does not prove live Twilio or Render operation.
- **Still pending:** authenticated browser smoke test, actual SMS A2P approval/STOP handling, live Resend and Stripe sandbox verification, confirmation of backup/restore and diagnosis of unusual calendar storage growth. Do not deploy solely on the results above.
- User alone installs, commits, pushes and deploys. No GitHub or Render changes were performed.

### Local install/validation commands after reviewing the exact working tree
```bash
cd ~/doorks-deploy-edit
git status --short
# Make a local backup and confirm the current source still matches the Nov 18 baseline.
unzip -o ~/Downloads/Doorks_Moses_527_Cumulative_Release_Gate_Review.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
# ONLY after your release approval, and after inspecting git diff:
git add main.py requirements.txt static/app.js static/moses_action_center.js static/moses_drafts.js app/routers app/services app/resources tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.27 cumulative readiness audit"
git push origin main
```

## Moses 5.28 — storage safety preflight and package reconciliation
- Added `scripts/pds_storage_preflight.py`, a read-only diagnostic that walks only a selected existing data directory without following symlinks. Reports disk capacity, largest files, folder totals, and scan errors. **Does not modify, truncate, delete, or back up any production data.**
- This is especially relevant because the production `/data/calendar` directory was reported at 9.7 GB before the existing Render disk was expanded from 10 GB to 25 GB. Growth cause is **not yet established**. Do not automatically clean up the calendar directory.
- Local demonstration (do not run on production without user's explicit decision): `python3 scripts/pds_storage_preflight.py --data-dir ./data`
- If the user chooses to run this command in Render Shell later, the path must be the existing durable directory (`/opt/render/project/src/data`) and output must be reviewed before any retention policy is proposed.
- 5.27 ZIP byte-for-byte reconciled against working source copy before this patch was assembled. Added 3 new focused tests covering byte counts, read-only behavior, and symlink exclusion.
- Tests on uploaded working source + cumulative changes: **842 passed, 2 skipped**. No credentials, production data, provider sends, or deployments performed.
- **Not yet deployment-certified:** actual authenticated browser smoke tests, PDS multi-estimate handoff, Twilio A2P approval and signed callback tests, Resend delivery, Stripe sandbox transactions, provider tool execution and durable restore tests still need direct verification. A passing local test suite alone is not a production rollout sign-off.

### Suggested final candidate validation, before user installs or pushes
```
cd ~/doorks-deploy-edit
# Preserve a backup of the existing project and check local edits first:
git status --short
# Confirm source files match the baseline before applying the cumulative patch.
# Do not overlay if main.py or static/app.js contain newer unmerged local changes.
unzip -o ~/Downloads/Doorks_Moses_528_Cumulative_Storage_Preflight.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/ --disable-warnings
python3 -m compileall -q main.py app scripts/pds_storage_preflight.py
node --check static/app.js
node --check static/moses_action_center.js
git diff --stat
# User alone authorizes commit/push/deploy after checking the changes and release gates:
git add main.py requirements.txt app/ static/ tests/ scripts/pds_storage_preflight.py CUMULATIVE_RELEASE_REVIEW.md
git commit -m "Moses 5.28 cumulative workflows and storage preflight"
git push origin main
```
The `git add` command above stages all modified files under those folders; review `git diff --cached --stat` before committing to avoid staging unrelated local changes. No command is run for the user.

## Moses 5.29 — consolidated patch compatibility gate (November 18)
- The 5.28 cumulative patch was verified against its current source-copy files, then repackaged as **one** cumulative 5.29 patch. **Do not stack 5.17–5.28 ZIPs**.
- Added `scripts/cumulative_baseline_manifest.json` with SHA-256 checksums for the **40 prior patch paths**: 14 files modified from the original user-uploaded `doorks-deploy-edit(6).zip`, and 26 files added relative to that snapshot. The manifest does not include production customer data or private credentials.
- Added read-only `scripts/check_cumulative_baseline.py` and four tests. It stops installation if local source has diverged from the Nov 18 snapshot, protecting newer Mac edits from accidental overwrite. It does not modify or deploy anything.
- Full local suite **846 passed, 2 skipped**. Python compilation, JS syntax and archive consistency must also be checked when assembling final ZIP.
- **Not production-cleared:** authenticated browser workflows, external provider verification (Twilio A2P, Resend, Stripe), Moses live SDK tool execution and persistent data recovery remain unverified. PRIO Coin is still a protected prototype.

### Safe application checklist (user runs these locally; no command below pushes or deploys)
```bash
cd ~/doorks-deploy-edit
git status --short
# Download the single 5.29 ZIP. Extract ONLY its three preflight files to a temporary folder first.
mkdir -p /tmp/doorks-529-preflight
unzip -o ~/Downloads/Doorks_Moses_529_Cumulative_Consolidated_Preflight.zip 'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-529-preflight
python3 /tmp/doorks-529-preflight/scripts/check_cumulative_baseline.py --root ~/doorks-deploy-edit --manifest /tmp/doorks-529-preflight/scripts/cumulative_baseline_manifest.json
# STOP if any baseline mismatch or if there are unrelated uncommitted edits.
# Only after inspecting changes and making a local backup:
unzip -o ~/Downloads/Doorks_Moses_529_Cumulative_Consolidated_Preflight.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
# COMMIT/PUSH remain entirely the user's decision in a separate, approved deployment window.
# When approved: git add ONLY the confirmed modified files; review git diff --cached.
# git commit -m "Doorks Moses 5.29 consolidated release candidate"
# git push origin main
```

## Moses 5.30 — scheduler email approval deduplication / predeployment pass
- Continues from the single 5.29 cumulative package and the original November 18 user-uploaded working-code snapshot; do not stack earlier ZIPs.
- Corrected a double-click race in Scheduler email *proposal* preparation. Same job + verified recipient + category + subject + body with status `pending` now reuses the existing approval under an SQLite `BEGIN IMMEDIATE` transaction. Distinct messages remain independently reviewable; rejected messages can be prepared again. No messages are sent on proposal creation.
- Existing office-admin authorization, sender disable flag, explicit approval, uncertain-outcome protection, and job history are retained. This does not prove live Resend delivery or Twilio messaging.
- Local suite: **849 passed, 2 skipped**; Python compilation, JS syntax and package consistency verified. Browser/provider/durable backup checks remain pending; this is not a deployment authorization.
- User alone installs, commits and pushes. No GitHub or Render modifications were made.

### Review commands for the cumulative 5.30 archive
```bash
cd ~/doorks-deploy-edit
git status --short
# Save a separate backup first and run the shipped read-only baseline checker
# First examine the bundled baseline checker in a separate directory before applying the patch.
# Never overwrite a diverged working tree.
# After reviewing the baseline check and approving differences, apply the ONE ZIP:
unzip -o ~/Downloads/Doorks_Moses_530_Cumulative_Release_Safety.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
# Only after live operational checks and explicit approval:
git add main.py requirements.txt static/app.js static/moses_action_center.js static/moses_drafts.js app/routers app/services app/resources scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.30 cumulative release safety"
git push origin main
```

## Moses 5.31 — SMS proposal/send parity and predeployment guard
- Carries forward **all** 44 paths from the 5.30 cumulative ZIP. Do not stack previous archives.
- Preparing an identical SMS twice for the same job, verified phone, and message reuses the existing *pending* approval under a serialized SQLite transaction. Different messages remain separate; rejected messages may be prepared again. No text is sent by proposal creation.
- Before an approved text is sent, the stored destination is revalidated against the **current** saved PDS job. If a customer phone number changed after proposal creation, approval blocks with a 409 and leaves the request pending.
- Current consent, exact PDS job, admin-only authorization, provider preflight, and uncertain-send anti-retry guards remain required. Twilio A2P activation and live delivery have not been tested.
- Local tests: **852 passed, 2 skipped**. Python compile and JS syntax checks passed. ZIP matches local cumulative source.
- **This is NOT permission to deploy.** Live provider/browser/backup and the broader Moses release-readiness checks remain outstanding; the user alone installs, commits, pushes and deploys.

### Suggested post-review commands (only after current Mac source compatibility check)
```bash
cd ~/doorks-deploy-edit
git status --short
# First run the existing read-only scripts/check_cumulative_baseline.py extracted from this ZIP.
# Do not overwrite newer local changes or deploy into the live app during office hours.
unzip -o ~/Downloads/Doorks_Moses_531_Cumulative_SMS_Approval_Safety.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
# Only after explicit release approval:
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.31 cumulative SMS approval safety"
git push origin main
```

## Moses 5.32 — Twilio early-status callback integrity
- This single cumulative patch supersedes 5.31; apply it **alone** to a compatible local project snapshot.
- Outbound Twilio `StatusCallback` URLs now carry the immutable approved proposal ID in the URL query. Twilio signs that complete URL; the webhook verifies the signature before using the ID. Existing callbacks without an ID remain compatible after their provider SID has been saved.
- An authenticated, signed delivery callback arriving before the outbound provider response is durably correlated to the already approved, in-flight proposal. Pending/unapproved proposals and mismatched provider SIDs cannot be claimed by callbacks.
- Out-of-order `queued`/`sent` events cannot downgrade an already delivered/undelivered/failed receipt. The send response no longer overwrites an earlier final callback.
- No new public unauthenticated action endpoints, Twilio live requests, or changes to scheduling/customer records were made by this patch.
- Local regression: **854 passed, 2 skipped**. Python compile, JS syntax, archive verification checked. Twilio A2P approval, live provider delivery, browser smoke testing, and backups are still deployment gates. **Not production sign-off.**
- User retains exclusive control of Git commits, push and Render deployment.

### 5.32 install commands — after release approval only
```bash
cd ~/doorks-deploy-edit
git status --short
# Extract the preflight checker/manifest from the ZIP to a temporary location first,
# inspect them, and run the checker against your current local project before overwriting.
mkdir -p /tmp/doorks-532-preflight
unzip -o ~/Downloads/Doorks_Moses_532_Cumulative_Twilio_Receipt_Integrity.zip \
  'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-532-preflight
python3 /tmp/doorks-532-preflight/scripts/check_cumulative_baseline.py \
  --root ~/doorks-deploy-edit \
  --manifest /tmp/doorks-532-preflight/scripts/cumulative_baseline_manifest.json
# If clean, back up the checkout, then apply the one cumulative ZIP (not the older ZIPs).
unzip -o ~/Downloads/Doorks_Moses_532_Cumulative_Twilio_Receipt_Integrity.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --stat
git diff --check
# Only after review and explicit approval to push:
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.32 cumulative Twilio receipt integrity"
git push origin main
```

## Moses 5.33 — cumulative HTTP integration smoke verification
- Supersedes all earlier cumulative patch ZIPs, including 5.32. Only the new HTTP smoke tests and updated preflight manifest/review notes are added; existing 5.32 application logic remains unchanged.
- Added 3 real-app FastAPI HTTP smoke tests verifying: public opt-in and policy URLs serve without a login; unsigned Twilio inbound/status callbacks are rejected; unauthenticated Scheduler email, SMS, and Van Stock write calls are denied. These run offline and never contact Twilio or Resend.
- Full local suite: **857 passed, 2 skipped**; 4 Python 3.13 multiprocessing deprecation warnings. No authenticated-browser or live-provider tests were executed. The release is **not yet production-qualified**.
- Final deployment remains user-controlled. Do not push into the live Render service until current Mac checkout matches baseline and real workflow/provider tests have been completed.

### 5.33 local review and Git commands (only when user chooses rollout)
```bash
cd ~/doorks-deploy-edit
git status --short
mkdir -p /tmp/doorks-533-check
unzip -o ~/Downloads/Doorks_Moses_533_Cumulative_HTTP_Smoke_Preflight.zip 'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-533-check
python3 /tmp/doorks-533-check/scripts/check_cumulative_baseline.py --root ~/doorks-deploy-edit --manifest /tmp/doorks-533-check/scripts/cumulative_baseline_manifest.json
# Stop if baseline check fails, and back up your local checkout before applying the patch.
unzip -o ~/Downloads/Doorks_Moses_533_Cumulative_HTTP_Smoke_Preflight.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --check
git diff --stat
# Only after you personally approve deployment and review staged files:
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.33 cumulative HTTP smoke preflight"
git push origin main
```

## Moses 5.34 — bounded calendar storage diagnostic and release audit
- This cumulative ZIP supersedes 5.33; install only the latest cumulative ZIP against the compatible Nov 18 working snapshot.
- The **read-only** `scripts/pds_storage_preflight.py` now uses a bounded top-N heap so it does not retain a record for every file in a heavily populated calendar directory. It also reports `calendar_breakdown_bytes` by immediate calendar subfolder (including `uploads`) to help investigate the prior 9.7 GB growth without reading, editing, or removing production records.
- Tests exercise 151 calendar files and verify that only the requested largest entries are retained, that subfolder sizes are accurate, and that top=0 is permitted.
- Full local automated suite: **858 passed, 2 skipped**; syntax and ZIP checks performed. This is an offline source candidate, **not yet production approved**. Authenticated browser testing, Moses live execution, Resend/Twilio A2P and send verification, Stripe sandbox, and recoverable backup remain outstanding.
- Release gate must also confirm the current Mac working checkout matches the original snapshot; do not overwrite diverged local files.
- Only the user commits, pushes and deploys. No live Render or GitHub mutations took place.

### Local preflight, install and test steps — only after user chooses the rollout window
```bash
cd ~/doorks-deploy-edit
git status --short
mkdir -p /tmp/doorks-534-check
unzip -o ~/Downloads/Doorks_Moses_534_Cumulative_Storage_Diagnostics.zip 'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-534-check
python3 /tmp/doorks-534-check/scripts/check_cumulative_baseline.py --root ~/doorks-deploy-edit --manifest /tmp/doorks-534-check/scripts/cumulative_baseline_manifest.json
# Stop if baseline check fails; back up the checkout and review before extracting.
unzip -o ~/Downloads/Doorks_Moses_534_Cumulative_Storage_Diagnostics.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --check
git diff --stat
# Only when user approves the final release after browser/provider verification:
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.34 cumulative release diagnostics"
git push origin main
```

## Moses 5.35 — signed Twilio HTTP flow acceptance check
- Cumulative patch, relative to the original uploaded `doorks-deploy-edit(6).zip`, superseding 5.34.
- Added real-FastAPI, offline signed webhook tests for START → YES → STOP with temporary SQLite consent storage, replay idempotence, signed-message tampering, and mismatched Twilio destination. No provider API requests were made.
- Added the new test path to the pre-unzip baseline compatibility manifest so an unexpected existing local file will block overwrite.
- Local automated suite: **860 passed, 2 skipped**; provider delivery, Twilio A2P approval, authenticated browser workflows, live Moses AI execution, Resend/Stripe tests and production backup remain unverified.
- The public policy/opt-in pages remain candidates until their actual published URLs and real message flow are validated. Keep `PDS_SMS_SEND_ENABLED=false` until the user tests and authorizes rollout.
- User alone chooses when to install, commit, push, or deploy. No GitHub or Render action was taken.

### One cumulative ZIP installation process (when the user chooses deployment)
```bash
cd ~/doorks-deploy-edit
git status --short
mkdir -p /tmp/doorks-535-preflight
unzip -o ~/Downloads/Doorks_Moses_535_Cumulative_Signed_SMS_Acceptance.zip 'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-535-preflight
python3 /tmp/doorks-535-preflight/scripts/check_cumulative_baseline.py --root ~/doorks-deploy-edit --manifest /tmp/doorks-535-preflight/scripts/cumulative_baseline_manifest.json
# STOP if the compatibility check fails. Back up the current checkout first.
unzip -o ~/Downloads/Doorks_Moses_535_Cumulative_Signed_SMS_Acceptance.zip -d ~/doorks-deploy-edit
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --check
git diff --stat
# ONLY after browser/provider/backup checks and user approval:
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md
git diff --cached --stat
git commit -m "Doorks Moses 5.35 cumulative SMS acceptance preflight"
git push origin main
```


## 5.38 controlled deployment packaging
Local suite 870 passed / 2 skipped. Exact payload hash check added. Live-provider and authenticated browser signoff remain operator-controlled.
