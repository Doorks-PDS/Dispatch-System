# Doorks / Moses 5.43 — Van Stock, Parts List, PDS Accounting, SMS policy & Moses

**Install only on an existing 5.42 source checkout.** This is a changed-files-only patch. Do not install the 5.38–5.42 ZIPs again. Never extract data, overwrite live PDS records, or use `git add .`.

## What changed

- PDS completion form Door Records is an icon-marked collapsible section.
- Van ticket part search opens the catalog when focused, including when the field is blank; type to filter.
- Van ticket has action buttons for load, return, used on job, van-to-van transfer and physical count. Quantities still travel through the existing locked stock ledger.
- Standard Van Stock Template now shows saved parts with edit/remove controls. Changes apply to future vans; existing vans retain their settings.
- Van-specific part settings may be edited or removed (only after its quantity reaches zero); no stock event is deleted.
- Office-only vehicle information includes fleet label, plate/VIN, insurance, registration and service notes; no separate store or login system.
- Physical van counts have a source-status and may be linked to an office source-reference review. A count is an opening or adjustment record, **not** a warehouse transfer, purchase or tax posting.
- PDS Parts List now shows warehouse quantity, van quantity, and total physically tracked; PDS Inventory & Receiving shows those quantities and movement history. No artificial GL/expense entries or values are posted.
- Moses answers stock shortage and saved job quote-scope questions using PDS records even when the general LLM tool executor cannot provide them. An explicit, verifiable appointment email request may create only an **unsent** Scheduler approval; approval/sending remains separate.
- Public `/pds/sms`, `/pds/sms/privacy`, `/pds/sms/terms` pages stay viewable while Twilio is being configured. The signed callbacks **still require** `PDS_SMS_PUBLIC_BASE_URL` and `TWILIO_AUTH_TOKEN`.
- Quote scope inspection also considers meaningful technician notes without labeling every routine PM as a new estimate.

## Apply safely on your Mac

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-543-check
unzip -o ~/Downloads/Doorks_Moses_543_Business_Inventory_Moses.zip \
  scripts/check_moses_543.py scripts/moses_543_manifest.json -d /tmp/doorks-543-check
python3 /tmp/doorks-543-check/scripts/check_moses_543.py --root "$PWD" --phase before
```

**STOP if the before check fails.** Preserve newer local changes; reconcile rather than overwriting them.

```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_543_Business_Inventory_Moses.zip -d .
python3 scripts/check_moses_543.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q app main.py
node --check static/app.js
git diff --check
```

Expected in the packaged local test environment: **896 passed, 2 skipped**. Your Mac environment may differ; stop on any failure.

## Git commands — run only after verification and when ready for Render auto-deployment

```bash
cd ~/doorks-deploy-edit
git add \
  app/routers/doorks_assistant.py app/routers/pds_sms.py app/routers/pds_van_stock.py \
  app/services/moses_pds_estimate_scopes.py app/services/moses_pds_verified_shortcuts.py \
  static/app.js \
  tests/test_moses_543_verified_shortcuts.py tests/test_pds_543_ui_routes.py \
  tests/test_pds_543_van_source_reconciliation.py tests/test_pds_sms_webhook_security.py \
  scripts/check_moses_543.py scripts/moses_543_manifest.json MOSES_543_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Doorks Moses 5.43 - PDS van and inventory reconciliation, UI and AI Butler"
git push origin main
```

The commit will trigger Render auto-deploy if that service is still set to auto-deploy on `main`. Nothing is pushed or deployed by the creation of this ZIP.

## Twilio A2P URLs (confirm each loads after your push)

- Signup/opt-in proof: `https://dispatch-system-pl8q.onrender.com/pds/sms`
- Privacy Policy: `https://dispatch-system-pl8q.onrender.com/pds/sms/privacy`
- Terms & Conditions: `https://dispatch-system-pl8q.onrender.com/pds/sms/terms`

The pages must be publicly accessible and accurately describe the **actual** keyword opt-in process. Do not assume successful A2P approval or live delivery from the HTML alone. You will need to configure the Twilio webhook to the signed inbound endpoint once campaign approval and sender setup are complete.

## After deployment — controlled tests

1. Check PDS login and existing tickets/calendars first. Open a completion form and expand 🚪 Door Records.
2. Van Stock: click an empty part search field. It should display a browsable list, then narrow as you type.
3. Edit a standard template item; confirm an existing van stays unchanged. Edit an item on a specific van.
4. Enter vehicle details, save, refresh, and verify. Technicians should not see office-only fields.
5. On a safe test van, enter an existing physical count. It must increase van stock without decreasing warehouse stock; source review should appear pending. Attach a reference and confirm it is recorded without financial posting.
6. Transfer recorded warehouse inventory to a van; warehouse declines, van rises, total tracked stays equal. Record usage, then check total tracked declines **once** (and warehouse does not decline twice).
7. Confirm Parts List and Accounting Hub Inventory & Receiving show the same stock numbers and movement history. Do not infer tax values or expenses from quantities alone.
8. Ask Moses: "Which vans need restocking?", "Review job 1126-15 and identify separate estimate scopes", "Show unverified van stock counts".
9. Ask Moses to prepare (not send) an appointment confirmation for a **future scheduled** test job with verified email. Confirm one pending proposal, **no email sent**.
10. Open the public SMS URLs, then complete A2P review separately; SMS remains disabled until you authorize live tests.

## Explicit boundaries

- Source tests are not proof of authenticated UI behavior or live Twilio/Resend delivery.
- PRIO Coin remains the existing admin trial prototype; this release does not create a regulated financial plan.
- PDS inventory is now reconciled by **quantity** across locations. It is **not** a completed cost-accounting, tax, asset valuation, or QuickBooks replacement system. Actual purchase cost/accounting postings still require separate verified processes.
- Physical counts with unverified provenance are **not** presented as documented purchases.
- No GitHub/Render changes were performed by this patch-generation process.
