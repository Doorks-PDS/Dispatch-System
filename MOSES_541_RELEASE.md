# Doorks / Moses 5.41 — Van Stock and PRIO Trial Dashboard

Applies **directly on top of committed Moses 5.40**. Do not reinstall 5.38 or 5.39. Only files in this ZIP change. No production data, attachments or credentials are included.

## Implemented
- Van setup excludes inactive login accounts and inactive employee records; it retains historical van ledgers.
- Parts in van tickets, stock movements and standard template now use typed, filtering search against the existing PDS Parts List. Selection binds the real part ID.
- Van tickets have clearer card layout and status. Existing inventory movement semantics are untouched.
- PRIO Coin now opens **within PDS Office Flow**, not a new tab, with 50/50 donut display and separate durable admin-only simulation ledger for trial amounts/notes/frequency. No real assets, payroll, distributions, or employee benefits are affected.
- The old `/pds/prio-coin-preview` URL remains protected for legacy compatibility but is no longer used by navigation.

## Mac check and install (you do this; nothing auto-deploys)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-541-check
unzip -o ~/Downloads/Doorks_Moses_541_Van_Stock_PRIO_Trials.zip \
  scripts/check_moses_541.py scripts/moses_541_manifest.json -d /tmp/doorks-541-check
python3 /tmp/doorks-541-check/scripts/check_moses_541.py --root "$PWD" --phase before
# Only continue after PASS
unzip -o ~/Downloads/Doorks_Moses_541_Van_Stock_PRIO_Trials.zip -d .
python3 scripts/check_moses_541.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Commit and push **only after testing**

```bash
cd ~/doorks-deploy-edit
git add main.py static/app.js app/routers/employees.py app/routers/pds_van_stock.py \
  app/routers/pds_prio_trials.py tests/test_prio_coin_admin_navigation.py \
  tests/test_pds_van_stock_ticket_ui.py tests/test_pds_prio_trials_541.py \
  tests/test_pds_van_active_541.py scripts/check_moses_541.py \
  scripts/moses_541_manifest.json MOSES_541_RELEASE.md
git diff --cached --check
git diff --cached --stat
git commit -m "Doorks Moses 5.41 - Van Stock active roster and PRIO trials"
# Pushing main triggers the live Render deployment; do so only when you choose:
git push origin main
```

## Live acceptance checklist
1. In **PDS > Forms > Van Stock**, confirm former/inactive employees are absent from setup; current techs and leads remain visible.
2. Set up one van. Search by part number or description in the ticket, select a result, and configure optional minimum/target.
3. With a verified warehouse count, load a part onto the van; check warehouse decreases once and van increases once. Test `Used on job` with a real job number.
4. Visit **PDS > Office Flow > PRIO Coin**: it stays inside the app; refresh and confirm trial entries persist; export the JSON. No payroll data should change.
5. Ask Moses: "Which vans are below their configured minimum?" and "Who has part [part number]?". Confirm it uses actual records.
6. Ask Moses: "Review job [number], identify separate estimate scopes" and "Prepare a customer email for job [number]". Do not approve sending until addresses and sender readiness are confirmed.
7. Keep Twilio SMS / Scheduler email outbound disabled until their provider and consent tests are verified.

**Scope note:** PRIO trial ledger is simulation-only and protected on PDS storage. It is not a financial product or live benefit plan. Moses AI tool calls still require live provider testing.
