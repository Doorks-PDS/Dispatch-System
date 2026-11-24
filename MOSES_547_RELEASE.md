# Doorks / Moses 5.47 — Dispatch Intake Review + QuickBooks PO References

Applies only over the **corrected Doorks / Moses 5.46** version. This is a small incremental patch and not a full replacement project.

## Changes

- The existing PDS New Dispatch AI intake now shows extracted details as editable, checkbox-selectable drafts; applying requires a separate click and replacing populated values requires confirmation. A job is still saved only with the normal Save button.
- Saved-customer matching suggests canonical variations (for example, “Irvine Company” versus “The Irvine Company”) and lets the user browse/search every saved customer, but does not automatically attach a potentially wrong account or address.
- A PDS ticket offers **Upload QB PO** beside its existing Purchase Order creator. The upload opens the existing document library with document type and job reference prefilled, and preserves the original QuickBooks PO number. It stores a reference document, **not** a newly numbered PDS PO or received inventory.
- Creating a new PDS PO from a job now opens the existing editor with job number, customer, and job description prefilled for review; no PO is saved until the user saves.
- The OpenAI Agents SDK remains the single Moses conversational path. Optional hosted web search from 5.46 is controlled by `DOORKS_MOSES_WEB_SEARCH_ENABLED`, remains disabled by default, and requires a live test. No new autonomous financial actions or customer sends are authorized by this patch.

## Safe install

```bash
cd ~/doorks-deploy-edit
mkdir -p /tmp/doorks-547-precheck
unzip -o ~/Downloads/Doorks_Moses_547_Intake_QB_PO.zip scripts/check_moses_547.py scripts/moses_547_manifest.json -d /tmp/doorks-547-precheck
python3 /tmp/doorks-547-precheck/scripts/check_moses_547.py --root "$PWD" --manifest /tmp/doorks-547-precheck/scripts/moses_547_manifest.json --phase before
```

Stop if the before check does not pass. Then:

```bash
unzip -o ~/Downloads/Doorks_Moses_547_Intake_QB_PO.zip -d .
python3 scripts/check_moses_547.py --root "$PWD" --phase after
source .venv/bin/activate
python3 -m pytest -q tests/
python3 -m compileall -q main.py app
node --check static/app.js
node --check static/moses_identity_review.js
git diff --check
```

Then stage **only** the changed release files. Do not use `git add .`:

```bash
git add static/app.js static/moses_identity_review.js tests/test_moses_547_intake_qb_po.py scripts/check_moses_547.py scripts/moses_547_manifest.json MOSES_547_RELEASE.md
git diff --cached --stat
git diff --cached --check
git commit -m "Doorks Moses 5.47 - reviewed dispatch intake and QuickBooks PO references"
git push origin main
```

## Acceptance checks

1. New Dispatch > AI Intake: upload a test work order. Confirm that customer identity and extracted fields are not saved automatically; adjust one suggested value, apply, and verify in the form.
2. Test a source naming “Irvine Company” against saved “The Irvine Company.” Manually select the saved account. Verify another similarly named customer is never auto-selected.
3. From a test dispatch ticket, choose Upload QB PO, attach a dummy QuickBooks PDF and original PO number, then confirm the Document Library shows the correct job number.
4. On a test dispatch, choose Purchase Order and verify customer/job number are populated. Cancel to ensure no numbered PO was created.
5. Confirm Estimate and Invoice actions still work and Moses reads PDS records. For SDK web search, perform a separately controlled real API test before enabling the feature flag.

No customer sends, document issuance, external SDK calls, database mutations, Git pushes or Render deployments are performed by this package build.
