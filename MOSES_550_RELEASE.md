# Doorks / Moses 5.50 — Compact PDS Generator & Roles (cumulative from 5.46)

**One archive replaces the undeployed 5.47, 5.48 and 5.49 ZIPs.** Only install over the exact **5.46 corrected** source snapshot when the compatibility check returns PASS. Do not install 5.49 separately. No data, users, secrets, uploads, payment receipts or calendar records are included in this patch.

## Generator revisions

- One document-type selector supports **Estimate**, **Invoice** and **Purchase Order**. The third option is shown only to leads/office. Choosing PO opens the **existing PDS supplier PO editor**—the purchase-order backend, original numbering, creator attribution, receiving and supplier tracking are preserved. PO is not produced by the estimate/invoice PDF endpoint. Switching out of an unsaved customer document asks for confirmation.
- Existing customer Estimate/Invoice generator starts with **Trip Charge $175**, **Fuel Surcharge $20**, and **one blank row**. Default service charges remain editable and pricing settings unchanged. Blank untouched rows are excluded from validation and saving; partially filled rows must still pass shared validation.
- Compact **Description Source + ✨ Auto Fill** controls replace the prior long guidance.
- A **single search box** finds standard Trip/Fuel/Labor/Crew/Freight charges and saved PDS Parts List entries; focusing the box offers options without typing. Typing in a line description also proposes matching charges/parts. Prices and taxable status must be reviewed before issuing. Use **＋ Line** for an additional empty line.
- Cost breakdown and totals use flexible columns rather than the previous fixed 320px column; small screens still scroll the line-item table horizontally.

## PDS roles and document flow

- **Tech**: create/edit numbered estimates **and invoices**, propose and decide own unsent estimate/invoice email approvals, access external estimate/invoice reference documents. **Never** create/edit POs or access supplier receiving or accounting; cannot delete issued docs.
- **Lead**: estimates, invoices and POs, but supplier/warehouse/receiving actions remain office-only.
- **Office/admin**: existing broader rights unchanged.
- Authorization is checked on the **server**, not just by hiding the PO option. It is still important to test on real tech and lead logins.

## Cumulative functions carried forward from undeployed 5.47–5.49

- Editable Moses dispatch intake and saved-customer matching.
- Alternate Upload of original QuickBooks Estimate, Invoice and PO documents. Originals remain marked **External** in the job and saved document categories, with QuickBooks references preserved. Uploading a file does not issue a new Doorks/PDS numbered document, receive parts or post an accounting transaction.
- Full calendar day cells display as many complete job pills as fit; the day drawer retains the full list.
- Size limits for calendar attachments to reduce risk of recurring disk exhaustion; existing files are retained.
- Immutable PO Created By / Created At from the authenticated employee and latest Updated By.

## Preflight and deployment

1. Extract `scripts/check_moses_550.py` and `scripts/moses_550_manifest.json` alone to `/tmp/doorks-550-check`.
2. `python3 /tmp/doorks-550-check/scripts/check_moses_550.py --root "$PWD" --manifest /tmp/doorks-550-check/scripts/moses_550_manifest.json --phase before`
3. If PASS, unzip this archive over `~/doorks-deploy-edit`.
4. `python3 scripts/check_moses_550.py --root "$PWD" --phase after`
5. `python3 -m pytest -q tests/`, `python3 -m compileall -q main.py app`, `node --check static/app.js`, `node --check static/moses_identity_review.js`, `git diff --check`.
6. Git add **only the changed paths listed in the chat**, commit, and push **only after your explicit local acceptance**.

## Live acceptance / remaining limitations

Test a disposable estimate, invoice, supplier PO, external QuickBooks reference, and new tech/lead permissions. The invoice/estimate Resend send workflow still requires saved job recipient verification and explicit approval; a prepared draft is not evidence of delivery. Moses Agents SDK and optional web search depend on live Render configuration, and Twilio A2P/Resend live delivery remain to be verified. This release does not certify a QuickBooks replacement, bank reconciliation, or automated expense recognition.

No GitHub/Render deployment or provider action was performed while preparing this patch.
