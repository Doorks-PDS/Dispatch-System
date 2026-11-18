# Doorks / Moses 5.40 — Van Tickets + AI Scheduler Approval

**Single combined patch for installed 5.38**. Includes the earlier **undeployed 5.39 Van Stock patch**, so **do not install 5.39 separately**. No Render or GitHub operations performed by the assistant.

## Actual changes
- Van Stock ticket cards, photos, low-stock lists, shared PDS part editor and Moses URL/photo intake entry point (5.39).
- Moses PDS-only read-only van stock overview (5.39).
- NEW Moses tool to prepare an *unsent* Scheduler email request from a verified saved PDS job, using existing recipient verification and approval ledger. Exact duplicate pending proposals are reused. Only a human can approve in Scheduler.
- NEW Moses tool to inspect verified Scheduler email history (submission status is not proof of delivery; message bodies/recipient addresses are not returned to the model).
- Tests for approved-scope access, recipient changes, separate workspaces, duplicate requests and history.

**Deployment gate:** Local tests pass but **live Moses SDK execution, authenticated browser usability, Resend/Twilio delivery and A2P approval remain unverified**. PRIO Coin is still only a preview. Do not enable new outbound communications until verified.

## Mac install (DO NOT push until you choose to deploy)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-540-check
unzip -o ~/Downloads/Doorks_Moses_540_Combined_Van_Stock_AI_Butler.zip \
 'scripts/check_moses_540.py' 'scripts/moses_540_manifest.json' -d /tmp/doorks-540-check
python3 /tmp/doorks-540-check/scripts/check_moses_540.py --root "$PWD" --phase before
```

If and only if PASS:

```bash
cd ~/doorks-deploy-edit
unzip -o ~/Downloads/Doorks_Moses_540_Combined_Van_Stock_AI_Butler.zip -d .
python3 scripts/check_moses_540.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q app main.py
node --check static/app.js
git diff --check
```

The old 5.38 verifier hashes must not be reused on deliberately changed 5.40 files. Never `git add .` or stage local data or backups.

When **you** choose to deploy after checking the staged diff:

```bash
git add static/app.js app/routers/pds_van_stock.py app/services/moses_agent.py \
 tests/test_moses_platform_boundaries.py tests/test_pds_van_stock_ticket_ui.py \
 tests/test_moses_540_scheduler_agent.py scripts/check_moses_540.py \
 scripts/moses_540_manifest.json
git diff --cached --stat
git diff --cached --check
git commit -m "Moses 5.40 - van tickets and guarded scheduler email tools"
git push origin main
```

Do not push if preflight, tests or diff checks fail. Pushing to main automatically deploys to your live Render service.
