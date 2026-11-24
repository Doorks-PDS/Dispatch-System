# Doorks / Moses 5.55.2 — Combined UI Cache + Sidebar Order

**Base:** Moses 5.55 on `main` (`0807eb3`). This is a **single replacement for the unapplied 5.55.1 patch**. Do not apply the old 5.55.1 patch first. No production data or credentials are included.

## Changes

- All the pending **5.55.1** UI-loading fixes: content-hashed `app.js` and `style.css` URLs, `Cache-Control: no-store` on the main HTML page, stable right-aligned sidebar subtitles and notification badges.
- In the **PDS Job Flow** navigation, the visible order is now **Job Flow → To-Do List → All Jobs → Door Records**. Existing buttons and listeners are moved rather than recreated.
- Includes regression tests for UI asset caching, subtitle layout and navigation order.
- The 5.55 Supplier Pricing queue, combined calendar time-off entry, and PDS workspace repair are preserved from the existing 5.55 base; they are not reimplemented in this patch.

## Install (Mac — no deployment until tests pass)

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-5552
unzip -o ~/Downloads/Doorks_Moses_5552_UI_Cache_Nav_Order.zip -d /tmp/doorks-5552

git apply --check /tmp/doorks-5552/moses_5552.patch
# Only if PASS (no output from --check means PASS):
git apply /tmp/doorks-5552/moses_5552.patch

python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

**Do not apply the 5.55.1 patch separately.** If `git apply --check` reports a failure, stop and share the error. Do not use `--force` or apply to a different branch.

## Git (after the checks pass)

```bash
git add main.py templates/ui.html static/style.css static/app.js \
  tests/test_moses_38_interface.py tests/test_moses_548_calendar_fit.py \
  tests/test_moses_5551_asset_cache.py tests/test_moses_5552_nav_order.py \
  tests/test_moses_launcher_regression.py MOSES_5552_RELEASE.md

git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.55.2 - cache refresh and PDS navigation order"
git push origin main
```

After Render confirms the new deployment, reopen the app in Safari (Cmd+Shift+R once). Verify PDS Job Flow order, time-off grouping, Supplier Pricing, Fleet Hub badge/title alignment. These tests are source-level only, not proof of Render deployment or authenticated browser functionality.
