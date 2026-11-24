# Doorks / Moses 5.48 — Calendar Fit, Alternate Upload, Attachment Guard

Applies directly over **5.47**. Do not install over an earlier or modified base without reconciliation.

## Changes

- PDS calendar displays the maximum number of whole job pills that fit a fixed, equal-height day cell on the current screen; no static five-job limit. Clicking the day still opens every job. Approved time-off markers remain ahead of regular jobs.
- Ticket **Alternate Upload** is matched in size/color to Estimate, Invoice, and Purchase Order. User selects estimate/invoice/PO to add an existing external document to the PDS Document Library using the original number and job link; never issues a second PDS document or changes inventory.
- Calendar job/completion attachments enforce configurable 20 MB/file and 50 MB/batch caps before consuming full upload payloads. Existing files are never deleted.
- Frontend cache version incremented so browsers fetch the revised calendar code/CSS.

## Moses online research

The installed OpenAI Agents SDK already supports optional WebSearchTool, but **production availability is not verified by local tests**. To activate web research and the PDS agent in the existing Render environment (user action only), configure:

```
DOORKS_MOSES_PDS_AGENT_ENABLED=true
DOORKS_MOSES_WEB_SEARCH_ENABLED=true
OPENAI_API_KEY=<existing valid secret>
```

Confirm OpenAI Agents SDK import and model support through a non-sensitive live research test. Do not paste API keys into ChatGPT. Research is read-only/public reference; private customer records must not be included in public web queries.

## Storage

The previous 9.7 GB calendar directory size is not proof that attachments alone caused the growth. Run **read-only** `python3 scripts/pds_storage_preflight.py --data-dir /opt/render/project/src/data` in the Render shell to see calendar/uploads breakdown and largest files. Do not delete, prune or restore snapshots automatically. The new 20/50 MB limits only cap future attachments, not existing data.

## Install

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-548-check
unzip -o ~/Downloads/Doorks_Moses_548_Calendar_Alternate_Storage.zip scripts/check_moses_548.py scripts/moses_548_manifest.json -d /tmp/doorks-548-check
python3 /tmp/doorks-548-check/scripts/check_moses_548.py --root "$PWD" --manifest /tmp/doorks-548-check/scripts/moses_548_manifest.json --phase before
```

**Stop** unless PASS. Then:

```bash
unzip -o ~/Downloads/Doorks_Moses_548_Calendar_Alternate_Storage.zip -d .
python3 scripts/check_moses_548.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

## Git commands — after all tests pass

```bash
git add static/app.js static/style.css templates/ui.html app/routers/calendar.py tests/test_moses_38_interface.py tests/test_moses_548_calendar_fit.py scripts/check_moses_548.py scripts/moses_548_manifest.json MOSES_548_RELEASE.md
git diff --cached --stat
git diff --cached --check
git commit -m "Doorks Moses 5.48 - calendar fit and alternate documents"
git push origin main
```

Pushing main may deploy automatically; the user performs this step.
