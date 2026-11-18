# Doorks / Moses 5.38 — Controlled Deployment Handoff

**Source baseline:** Uploaded `doorks-deploy-edit(6).zip` (2026-11-18). This package replaces all previous cumulative patch ZIPs; never stack older versions first.

## Status
The assembled application is locally source-qualified. **Controlled code deployment only**, with outgoing Scheduler SMS and email disabled. This is **not** certification that Twilio A2P, Resend, Stripe, live Moses AI actions, or all browser workflows are ready. PRIO Coin is an **admin-only demonstration**; not live financial functionality. Avoid enabling unsupported features and do not run real PRIO allocations.

## Validated locally
- 870 tests passed, 2 skipped on Python 3.13 (2026-11-18).
- The existing FastAPI HTTP tests use mocked messaging providers; they **do not** send customer messages.
- Python compilation, critical JavaScript syntax, source manifest and archive integrity.
- Installation verification now checks that files match the exact packaged release.

## Before installing (your Mac only)
1. Confirm you are in `~/doorks-deploy-edit` on `main` and have a clean working tree. **Do not overwrite newer local edits.**
2. Back up the local project and confirm production backup and restore procedures. The old 9.7 GB calendar directory deserves monitoring, but do not delete production data.
3. Obtain this ZIP in `~/Downloads`.

```bash
cd ~/doorks-deploy-edit
git status --short
git branch --show-current
mkdir -p /tmp/doorks-538-precheck
unzip -o ~/Downloads/Doorks_Moses_538_Controlled_Deployment.zip 'scripts/check_cumulative_baseline.py' 'scripts/cumulative_baseline_manifest.json' -d /tmp/doorks-538-precheck
python3 /tmp/doorks-538-precheck/scripts/check_cumulative_baseline.py --root "$HOME/doorks-deploy-edit" --manifest /tmp/doorks-538-precheck/scripts/cumulative_baseline_manifest.json
```

**STOP if the precheck fails.** The ZIP was built against the uploaded Nov 18 snapshot—not an arbitrary newer checkout.

## Install and verify (your Mac only)
```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_538_Controlled_Deployment.zip -d ~/doorks-deploy-edit
python3 scripts/verify_cumulative_release_538.py --root "$HOME/doorks-deploy-edit"
python3 -m pytest -q tests/
python3 -m compileall -q main.py app scripts
node --check static/app.js
node --check static/moses_action_center.js
node --check static/moses_drafts.js
git diff --check
git status --short
git diff --stat
```

**Keep `PDS_SMS_SEND_ENABLED=false` and `PDS_SCHEDULE_EMAIL_SEND_ENABLED=false` on Render** for initial deployment. The source defaults to disabled when flags are absent; verify Render flags yourself before pushing. Do not share credentials in chat.

## Commit and deploy — USER ONLY, after the checks pass and you select a safe time
```bash
cd ~/doorks-deploy-edit
git add main.py requirements.txt app/routers app/services app/resources static/app.js static/moses_action_center.js static/moses_drafts.js scripts tests CUMULATIVE_RELEASE_REVIEW.md RELEASE_SIGNOFF_538.md
git diff --cached --stat
git commit -m "Doorks Moses 5.38 cumulative controlled deployment"
# git push origin main  # USER ONLY: will auto-deploy to Render when run
```

## Immediate post-deployment acceptance BEFORE enabling sends
- PDS office login, dispatcher/new ticket, job edit/save, attachments and multiple completion forms; Scheduler compact UI and notifications preview/history.
- Estimator: separate quote scopes, saved RE documents linked to the right job/forms, PDF download; prevent duplicate invoice/estimate sends.
- Van Stock: test a known part against a verified physical count, confirm warehouse reduction, transfer/usage audit trail, permissions, and optional reorder alerts.
- Moses: authenticated read, draft, approval, execution receipt; never infer success from prepared actions. Verify workspace isolation.
- Confirm persisted jobs/attachments after restart and available disk capacity; no accidental writes to historic PDS/SDC data.
- Publish public SMS sign-up/privacy/terms pages and obtain A2P approval; then test one opted-in real message and signed callback before enabling SMS.
- Verify Resend sender and reply routing with one controlled approved email before enabling Scheduler emails.
- Stripe sandbox webhook test remains required before live payments. PRIO Coin preview is **not** enabled for financial operation.

If any acceptance fails, leave SMS/email disabled and stop; retain source and storage backups. Do not delete, reset, or revert the persistent disk.

**This release changes files only. It does not deploy or send anything itself.**
