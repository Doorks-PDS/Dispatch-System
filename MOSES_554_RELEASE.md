# Doorks / Moses 5.54 — Job Flow, Recommendation Photos & Calendar Time Off

**Base:** Your corrected local Moses 5.53 source (`doork-deploy-Test.zip`), including the `Doorks_Moses_553_Alternate_Label_Test_Fix` test correction. This is an incremental **source-only patch**, not a full project deployment. No business data, secrets, credentials, database, Render configuration, or customer images are included.

## Job Flow / document preparation

- Moses Job Flow now has just **Quotes** and **Invoices**. Removes the redundant **Parts / Pricing** work queue and Job Flow button; parts lookup, new part, charges, freight and labor remain available inside document review and the existing estimator.
- **Draft Estimate** and **Draft Invoice** open the saved-form recommendation helper first, with **View Job**, **New Part**, and **Generate Estimate / Generate Invoice** controls. “Generate” proceeds to the **editable document generator**; it does not automatically issue, email, or charge anything.
- Each saved recommendation or completion form shows its **own saved image thumbnails** horizontally with compact arrows; click a thumbnail for the existing full-size attachment carousel with previous/next navigation. Image URLs remain tied to their saved form and job. No photos are copied into the source patch.
- For invoices, an eligible **saved Doorks estimate associated with the same job** can be chosen as the source. The user must explicitly confirm the quoted work was performed. Saved document line quantities, prices, tax settings and work description are brought into the **editable invoice**; helper defaults do not add trip/fuel/labor/parts again. Saved source is checked again before issuing. If there is no linked quote, create an independent T&M invoice.
- Suggested descriptions adapt proposal verbs to completed-work terms (e.g. “Furnish and install” → “Furnished and installed”). The user must still check actual completed work, partial jobs, exclusions, material quantities, labor, tax rate and terms before issuing; the tool does not independently verify completed installation.
- A saved estimate or invoice alone will **not** change job status to **Quote Sent** or **Done** or mark the estimate number as sent. Existing approved Resend delivery service handles confirmed-send status transitions.

## Calendar time off

- Approved overlapping staff absences appear in **one orange row per day**, e.g. **“Alfredo, Caleb, Steve Out”**. On narrower cells it displays a readable condensed name/count instead of clipping multiple pills.
- Click the orange row to open a **side drawer** listing each approved time-off request, employee, date range, notes, PTO and emergency flag when saved. The surrounding date still opens the existing daily schedule. Office users can open the regular Time Off Requests page from this drawer.
- Displays existing approved requests only. No request approvals, calendar jobs, employee balances, or payroll are changed.

## Verification

Source checks completed for this candidate: `node --check static/app.js`, `python3 -m compileall -q app`, and `python3 -m pytest -q tests/` → **949 passed, 2 skipped**. Five older assertion tests were adjusted to the requested replacement behavior; new tests exercise same-job quote matching, description conversion, photo URL linkage, single time-off pill and safe status semantics. No authenticated web-browser or live-provider acceptance test has been performed.

## Install over local 5.53 (not 5.51)

From `~/doorks-deploy-edit` on `main`, while your working files still match the provided 5.53 source:

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-554-check
unzip -o ~/Downloads/Doorks_Moses_554_Job_Flow_Calendar.zip 'scripts/check_moses_554.py' 'scripts/moses_554_manifest.json' -d /tmp/doorks-554-check
python3 /tmp/doorks-554-check/scripts/check_moses_554.py --root "$PWD" --phase before
# Only when the preceding command says PASS:
unzip -o ~/Downloads/Doorks_Moses_554_Job_Flow_Calendar.zip -d .
python3 scripts/check_moses_554.py --root "$PWD" --phase after
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
git diff --check
```

**Do not unzip if the before check reports STOP**. It means the provided local source differs from the base patch; reconcile first to avoid regressions. This ZIP contains only these edited files and 5.54 test/release helpers:

```
static/app.js
tests/test_moses_38_interface.py
tests/test_moses_45_direct_workflows.py
tests/test_moses_47_queue.py
tests/test_moses_554_job_flow_calendar.py
MOSES_554_RELEASE.md
scripts/check_moses_554.py
scripts/moses_554_manifest.json
```

### After your local acceptance

```bash
cd ~/doorks-deploy-edit
git status --short
git add static/app.js tests/test_moses_38_interface.py tests/test_moses_45_direct_workflows.py tests/test_moses_47_queue.py tests/test_moses_554_job_flow_calendar.py MOSES_554_RELEASE.md scripts/check_moses_554.py scripts/moses_554_manifest.json
git diff --cached --check
git diff --cached --stat
git commit -m "Moses 5.54 - job flow documents, recommendation photos and calendar time off"
git push origin main
```

**Live acceptance suggestions:** Open Moses Job Flow → Quotes and Invoices; view recommendation images and full size; generate a T&M invoice with no parts; choose a job-linked saved estimate and verify amounts are not duplicated, past-tense scope is editable, and no status change occurs before a confirmed send. Check November 23 in Calendar: one staff-time-off row and its side drawer, with normal jobs and date-click still working. Keep email sending and payments under existing manual approvals.
