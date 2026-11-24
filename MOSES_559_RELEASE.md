# Doorks / Moses 5.59 — corrected 5.58 → 5.59 incremental patch

**Apply to:** your existing local working tree with the **Moses 5.58 Resend + customer notification patch already installed but not committed/deployed**. This ZIP adds only the new Moses web/agent work; it intentionally does **not** reapply 5.58.

**Production baseline:** GitHub/Render were at 5.57 when this patch was created. Both your local 5.58 changes and these new 5.59 changes will be included when you eventually commit and push. No deployment was made by creating this patch.

## Changes in 5.59 (on top of 5.58)

- PDS office-admin conversations prefer the existing configured OpenAI Agents SDK agent instead of intercepting every query with legacy keyword shortcuts. Verified, read-only shortcut recovery remains available; business writes and sends are not automatically retried.
- Public reference web search uses the existing hosted `WebSearchTool`, limited by workspace permissions and explicit `DOORKS_MOSES_WEB_SEARCH_ENABLED=true`. The agent instructions forbid sending customer names, addresses, job numbers or private information to web search and request source URLs for researched claims.
- Adds an administrator-only synthetic diagnostic at `POST /doorks-assistant/agent-web-check` with request header `x-moses-validation: hosted-web-check`. Only a confirmed hosted `web_search_call` plus an answer can yield `web_search_verified: true`. This does not contact customers or modify business records.
- Adds readiness flags to the existing agent readiness response, reporting **configuration** rather than falsely asserting web access already works.
- **All 5.58 Resend and dispatch notification UI changes remain exactly as installed locally.** Supplier approvals, uncertain send handling and Twilio consent/sending guards are unchanged.

## Install (do not install the previous 5.59 ZIP)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-559-fixed
unzip -o ~/Downloads/Doorks_Moses_559_On_558_Corrected.zip -d /tmp/doorks-559-fixed
git apply --check /tmp/doorks-559-fixed/moses_559_on_558.patch
# ONLY after git apply --check succeeds with no output:
git apply /tmp/doorks-559-fixed/moses_559_on_558.patch
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

If `git apply --check` fails, **do not force it or reapply 5.58**. Share `git status --short` and the patch error so we can reconcile local changes without discarding them.

## Commit both unapplied versions together after tests pass

```bash
cd ~/doorks-deploy-edit
git add static/app.js static/style.css \
  app/routers/pds_supplier_quotes.py \
  app/routers/pds_schedule_notifications.py \
  app/services/pds_schedule_notifications.py \
  app/routers/doorks_assistant.py \
  app/services/moses_agent.py \
  app/services/moses_web_probe.py \
  tests/test_pds_vehicle_flow_544.py \
  tests/test_moses_558_email_setup_and_notification_ui.py \
  tests/test_moses_559_web_connection.py \
  MOSES_558_RELEASE.md MOSES_559_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.59 - web AI and cumulative Resend updates"
git push origin main
```

Don't stage a missing or unrelated file; inspect the staged stat before committing. This pushes both locally accumulated 5.58 and 5.59 changes, and Render auto-deploys from `main`.

## Required live configuration, **only after code deployment**

- `OPENAI_API_KEY`: actual secret in Render, never GitHub or chat; ChatGPT subscription does not include API billing. Check OpenAI API spending limits first.
- `DOORKS_MOSES_PDS_AGENT_ENABLED=true`
- `DOORKS_MOSES_WEB_SEARCH_ENABLED=true`
- `DOORKS_MOSES_MODEL=gpt-4.1-mini` (or another validated compatible model)
- `MOSES_LIVE_VALIDATION_ENABLED=true` **temporarily** for the web probe, then set to `false`.
- Keep `PDS_SMS_SEND_ENABLED=false` until A2P campaign approval, sender association and actual opt-in tests.
- Keep `PDS_SCHEDULE_EMAIL_SEND_ENABLED=false` until confirmed Resend delivery test and appropriate approval.
- Preserve the existing `MOSES_PDS_DISPATCH_REPLY_TO=reception@prioritydoors.com` and other PDS reply-to addresses in Render.

### Read-only hosted search verification

From an authenticated PDS office-admin browser session, after the above flags have been applied:

```js
fetch('/doorks-assistant/agent-web-check', {
  method: 'POST',
  headers: {'x-moses-validation': 'hosted-web-check'}
}).then(r => r.json()).then(console.log)
```

The web check uses a synthetic public documentation query; it does not read jobs or send communications. `web_search_verified: true` means a hosted search was seen in that response; it is **not** proof that all business tools work. Live agent execution, Resend delivery and SMS callbacks still require separate tests. Disable the temporary validation flag afterward.
