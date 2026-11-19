# Doorks / Moses 5.46 — Fleet Hub, Inventory Audit & Scheduler Controls

**Apply only to Doorks/Moses 5.45.** This is one incremental ZIP, containing changed files only. No user records, files in `data/`, database backups, or environment credentials are included. **No GitHub push or Render deployment was performed by the assistant.**

## Included

- **Fleet Hub:** technician/lead editing of their *own* assigned van; office/office-admin editing of all vans. Office-only: warehouse loads/returns, other-van transfers, standard stock templates, disable/enable, insurance and VIN edits. Field employees see non-sensitive read-only vehicle data and only their own stock-history actions.
- **Readable stock audit:** human descriptions, actor identity, date, reason, per-van before/after balance, warehouse effect. Historical records without actor retain an honest legacy label. Changes to van assignments, template entries, vehicle details and services are audited separately.
- **Fleet UI:** renamed Fleet Hub, compact view/edit vehicle information, no blank disclosure bar, hide administration controls from field staff.
- **Scheduler:** one Save Schedule button with a clear confirmation when planned date differs from original job date; staff/date/time rules preserved; Notify Customer presented as a button that reveals existing Email/Text/Both approval controls. Message sending remains gated by saved-contact verification and approval.
- **Inventory:** searchable inventory table now offers **Adjust Stock** for office users; uses existing audited `/data/parts/{id}/adjust-stock` endpoint, with quantity/reason and confirmation. Technician accounts cannot adjust warehouse quantities. Movement history is readable.
- **Receipt upload:** Field Flow no longer lists historical receipts; after upload, only a link to the just-uploaded document appears. Full receipt ledger remains in passkey-protected Accounting Hub.
- **Business Settings:** replace redundant estimate/invoice generator link with Customer & Contact Directory.
- **Scheduler roster:** only active PDS sign-in users offered for new assignments; archived assignments retained on historical tickets.
- **Moses:** existing SDK business action tools remain; optional hosted internet research (`DOORKS_MOSES_WEB_SEARCH_ENABLED=true`) is available *only if* the Agents SDK/runtime supports it and the authenticated agent is enabled. Off by default; web findings are not authorization to send or change business records. No live AI call is claimed.

## Limits and live QA

- SDK connectivity, real external search, Twilio A2P approval, and provider email/SMS delivery are **not verified** by local tests.
- Existing invoice/estimate and payroll operations remain unchanged. Stock movements and physical counts do not create accounting expenses/tax entries.
- If a field worker isn't linked to an active login/employee ID, own-van writes fail closed and the office must correct employee identity.
- Check after rollout: PDS login/calendar/jobs; scheduler saved date vs job date; active roster; notification approval (DO NOT send first); Fleet Hub permissions for a test tech and office admin; van stock usage and audit history; inventory quick adjustment with reversible test quantity; Accounting Hub receipts; Moses read-only answers.

## Before install

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-546-check
unzip -o ~/Downloads/Doorks_Moses_546_Fleet_Hub_AI_Butler.zip \
  scripts/check_moses_546.py scripts/moses_546_manifest.json \
  -d /tmp/doorks-546-check
python3 /tmp/doorks-546-check/scripts/check_moses_546.py \
  --root "$PWD" --phase before
```

## Install only if that prints PASS

```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_546_Fleet_Hub_AI_Butler.zip -d .
python3 scripts/check_moses_546.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Explicit Git staging (run ONLY after all checks pass)

```bash
cd ~/doorks-deploy-edit
git add \
  static/app.js \
  app/routers/pds_scheduling.py \
  app/routers/pds_van_stock.py \
  app/services/moses_agent.py \
  tests/test_moses_545_cumulative_workflows.py \
  tests/test_pds_vehicle_flow_544.py \
  tests/test_pds_van_stock_ticket_ui.py \
  tests/test_moses_546_fleet_permissions_audit.py \
  tests/test_moses_546_web_search_config.py \
  scripts/check_moses_546.py \
  scripts/moses_546_manifest.json \
  MOSES_546_RELEASE.md

git diff --cached --stat
git diff --cached --check
git commit -m "Doorks Moses 5.46 - Fleet Hub permissions and inventory audit"
git push origin main
```

Do not use `git add .`, and do not stage local users, receipts, databases, `.venv/`, or `.bak` files. Your push may trigger automatic production deployment.
