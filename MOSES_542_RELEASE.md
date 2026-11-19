# Doorks / Moses 5.42 — Van stock usage and cleanup

Incremental patch on top of **5.41**. No database migration, external messages, purchases, real PRIO funding, or production data files. Do not install older revisions separately.

## Included
- Standard van template saves defaults for **future van setup**. Existing van tickets are not silently changed when defaults are edited.
- Van ticket manual stock movements are collapsed until needed, with office-only warehouse/van transfers, physical counts, and manual job usage. Adds atomic **Van → Van** stock transfers.
- PDS completion forms now offer **optional explicit parts and quantities** from the selected technician's active van. They are matched to saved PDS part IDs, then recorded only **after** the completion form is saved, linked to its unique saved form ID.
- A completion usage line deducts **van** stock but not warehouse stock a second time. Retries use a deterministic key; repeated submission cannot double-deduct. Different quantities under the same form/part require manual review.
- Technicians can record only stock from their own matched van through the linked completion endpoint. Manual stock corrections and warehouse transfers remain office-only.
- Moses's existing read-only Van Stock tool now includes the most recent 30 stock movements to answer usage and replenishment questions with records instead of guesses. Moses cannot silently move inventory.

**Limitations:** The free-text Parts Used field does not trigger stock deduction; a technician must choose real PDS parts in the optional structured section. Completion-form saves and stock ledger changes are separate operations: if the stock step fails, the form stays saved and the UI displays a warning. Reconcile the affected part using the saved form ID; don't blindly record a second manual usage. Existing completion records are not retroactively modified. Live authenticated browser testing is still required before considering that flow fully verified.

## Install (Mac, existing main, you control Git and deployment)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-542-check
unzip -o ~/Downloads/Doorks_Moses_542_Van_Completion_Stock.zip scripts/check_moses_542.py scripts/moses_542_manifest.json -d /tmp/doorks-542-check
python3 /tmp/doorks-542-check/scripts/check_moses_542.py --root "$PWD" --phase before
# STOP if incompatible. Otherwise:
unzip -o ~/Downloads/Doorks_Moses_542_Van_Completion_Stock.zip -d .
python3 scripts/check_moses_542.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Stage only these files, inspect, then commit/push on your own schedule

```bash
cd ~/doorks-deploy-edit
git add static/app.js app/routers/pds_van_stock.py app/services/moses_agent.py \
  tests/test_pds_van_stock_http_acceptance.py tests/test_pds_van_completion_542.py \
  tests/test_pds_van_completion_ui_542.py scripts/check_moses_542.py \
  scripts/moses_542_manifest.json MOSES_542_RELEASE.md
git diff --cached --stat
git diff --cached --check
git commit -m "Doorks Moses 5.42 - linked van usage and stock reconciliation"
# ONLY if ready to automatically deploy PDS:
git push origin main
```

## Live acceptance after **you** deploy
1. Edit standard van template: an existing van keeps its own assigned parts; a newly created van inherits the template.
2. Create a completion form for a job and a technician with an enabled van. Expand *Parts used from technician van*; select the exact part, enter quantity, and save. Confirm one van deduction; warehouse remains unchanged.
3. Confirm the saved completion form still contains its Parts Used notes. Check the Van Stock movement history for the saved form ID. Repeat the same API submission only in a controlled test; it must report duplicate, not deduct again.
4. Confirm invalid part selection, wrong technician, missing form, and insufficient van count are rejected. Never perform this test on real stock without a safe test record.
5. Open the compact manual *Record Stock Movement* section. Transfer a test part from Van A to Van B; source falls, destination rises, warehouse unchanged.
6. Ask Moses: **"Which vans need restocking and what was the last van stock movement?"** He should report saved counts and movements without claiming he made changes.
7. Verify Dispatch, Schedule, Estimates, Invoices, and Moses chat. Review any stock reconciliation errors before permitting real team use.
