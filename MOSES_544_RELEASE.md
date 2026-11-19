# Doorks / Moses 5.44 — Vehicle Flow, Scheduler & Inventory

**Applies over 5.43, not over 5.42 or older.** Patch contains only changed/new source files. No real PDS data or credentials are included. Your Mac performs the commit and push; nothing here changes Render or GitHub automatically.

## Changes
- Scheduler Email/Text/Both: clearer verified job-contact recipient selection and retry after rejecting a proposal; appointment, schedule change and technician ETA templates include PDS callback (760) 233-5037 and reception@prioritydoors.com. No automatic sends. A recipient not present on the saved ticket remains blocked; update the saved contact first.
- Completion Form Door Records: searchable dropdown with browse-on-focus and matching by door ID, location, customer, address and manufacturer; existing door linkage remains ID-based.
- Vehicle Flow: renamed menu with left/right-aligned label and Fleet Info/Stock, Vehicle Info button before Disable Van, overdue-service indicator, immutable service/accident/inspection/notes history, stored on existing PDS durable van stock file with office-only write permissions.
- PDS Inventory & Receiving: compact searchable SKU table with warehouse, van, total, low-stock badge/filter and controlled pagination; detailed stock movement history is collapsible. No cost/tax postings are generated.
- Standard Van Stock template and stock movement logic retained unchanged.

## Install
First, run the compatibility check from a temporary directory, without overwriting any files:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-544-check
unzip -o ~/Downloads/Doorks_Moses_544_Vehicle_Flow_Notifications_Inventory.zip scripts/check_moses_544.py scripts/moses_544_manifest.json -d /tmp/doorks-544-check
python3 /tmp/doorks-544-check/scripts/check_moses_544.py --root "$PWD" --phase before
```

Only on PASS:

```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_544_Vehicle_Flow_Notifications_Inventory.zip -d .
python3 scripts/check_moses_544.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

**Expected on locally reconstructed 5.43 source:** 899 passed, 2 skipped. Live app browser and email provider validation are still required.

## Stage, commit, and push (user only)

```bash
cd ~/doorks-deploy-edit
git add static/app.js app/routers/pds_van_stock.py tests/test_pds_vehicle_flow_544.py scripts/check_moses_544.py scripts/moses_544_manifest.json MOSES_544_RELEASE.md
git diff --cached --stat
git diff --cached --check
git commit -m "Doorks Moses 5.44 - vehicle flow and notification refinements"
git push origin main
```

**Caution:** `main` auto-deploys on Render. Do not stage local data, `.venv`, backups or business records. Do not run `git add .`.

## Browser acceptance (after deployment)
1. Open old PDS job, use Door Records search to find/assign an existing door, save and confirm the correct door ID was linked.
2. Scheduler: prepare email on a test job with its actual saved contact, reject it, then prepare another. Check that rejected state does not block new pending approval. Deliberately enter a different address and confirm it is rejected with an explanation. Do **not** approve sending until provider test is authorized.
3. Check the preset callback number and reply email; ETA text should not imply a confirmed arrival time without one.
4. Vehicle Flow: service due on/before today should display a warning and icon in Vehicle Info; save a service and an incident and verify both survive refresh. Other roles cannot access private vehicle details or write log entries.
5. Accounting Hub → Inventory & Receiving: search by part and manufacturer; filter low stock and verify warehouse, van, and combined totals against Parts List and van ticket, then expand movement history.
6. Confirm no new accounting expense/tax posting occurs from a van count, history entry or template item.
7. Run Moses read-only prompts on real work orders; live AI tool execution and Twilio/Resend delivery are still separate checks.
