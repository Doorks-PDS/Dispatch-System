# Doorks / Moses 5.51 — Single cumulative generator + catalog update

**Install on the 5.46 source currently on GitHub `main`.** This release includes all cumulative, undeployed 5.47–5.50 files plus the additional 5.51 files. **Do not install 5.49 or 5.50 first.** Never apply if the `before` compatibility check fails; reconcile local differences first.

## 5.51 improvements

- **Estimate/Invoice Generator — Create Customer / Contact**: New `+ Customer` inside the open document editor. Enter customer name, address, phone/email, and optional contact. Saves through existing PDS CRM, auto-selects newly created customer, and preserves the unsaved document. Rejects likely duplicate company names, including a leading `The` variation. Existing records remain selectable.
- **Supplier PO — Create Vendor**: New `+ Add Vendor` beside the supplier finder in the existing PDS Purchase Order editor, supporting name, contact, mailing address, phone, email, terms, notes. Uses the existing PDS supplier store. Leads may create suppliers for POs, but cannot modify existing suppliers, perform receiving/warehouse movements, or access accounting. The supplier is automatically selected in the open PO draft.
- **Part/Service catalog**: The generator's parts/charges search always begins with `+ Add New Part or Service`. Inline modal captures SKU/service code, provider/manufacturer, description, supplier/subcontractor, cost, customer price, HTTPS product link and photo. Saves to the current PDS catalog first, then inserts a line into the existing estimate/invoice. Search and inline description matching distinguish services from stocked parts. Existing Parts List editors support the catalog classification.
- **Moses product website intake**: Both the existing Parts List editor and new inline part editor show a *reviewable field-by-field preview* of fetched public product-page metadata. The operator chooses which suggestions to apply before saving. Where structured metadata is incomplete, Moses optionally uses the configured OpenAI model to extract only missing facts from a bounded, sanitized public-page excerpt. The extract is not a purchase record; no supplier price or stock level is inferred. Unavailable/blocked websites still allow manual entry and photo upload. OpenAI extraction needs `OPENAI_API_KEY` in Render and can be disabled with `DOORKS_MOSES_PRODUCT_AI_ENABLED=false`.
- **Non-stock service safety**: Saved services have `item_type=service`; they appear in the catalog, are non-taxable by default in the generator (editable tax checkbox), but do not appear as warehouse/van stock. Backend stock adjustment rejects service IDs; fleet stock reads exclude them. Existing legacy parts are implicitly `part` and remain unchanged.
- **$190 trip default**: Existing PDS pricing defaults already say $190. The old generator incorrectly started new documents at $175. It now initializes trip/fuel lines from **saved** pricing, with $190 only as a missing-setting fallback. Existing saved estimates/invoices and price overrides are not rewritten.

## Still included from cumulative 5.47–5.50

Editable Moses dispatch intake and customer matching, QuickBooks Alternate Upload reference files linked to saved job and saved Estimate/Invoice/PO categories, calendar flexible-fit display and upload-size safeguards, protected PDS roles and PO creator audit, compact Estimate/Invoice/PO generator, and supplier receiving linkage.

## Role boundary

- Tech: create/edit and prepare approved email sends for Estimates and Invoices; no POs, warehouse receipts, or supplier administration.
- Lead: same plus create/edit POs and **create** new supplier profiles; existing supplier profile changes and warehouse/receiving remain office-controlled.
- Office/admin: broader PDS business/fleet/receiving access as already established. PDS photo upload still requires office-admin permission; other roles can enter a public photo URL.
- All approvals for customer email, payments, and financial operations remain in their existing provider-backed flows.

## Installation

1. Run 5.51 `before` compatibility check using the checker extracted to `/tmp` **without overwriting project files**.
2. If PASS, unzip 5.51 to `~/doorks-deploy-edit` and run 5.51 `after` compatibility check.
3. Run `python3 -m pytest -q tests/`, `python3 -m compileall -q main.py app`, `node --check static/app.js`, and `git diff --check`.
4. Stage only the paths enumerated in the final ChatGPT Git commands; do not stage `data/`, `.venv/`, or backup files. User controls `git push origin main` and Render auto-deployment.

## Live acceptance

- Create a test customer/contact from the open Estimate editor and confirm it is saved in PDS CRM without losing the draft.
- Create a test supplier as a lead from the PO editor; verify the same lead cannot edit an existing supplier or record receiving.
- Add a non-stock subcontractor service from the generator and confirm search can insert it into the current Invoice, without adding to inventory.
- Add a product by HTTPS page, review selected extracted metadata, save it and confirm the product appears in the Parts List; use a test website without a SKU to check the optional OpenAI fallback if enabled.
- Start a new Estimate and check trip is the **saved rate** ($190 if that's what's in Settings), not $175. Do not automatically update issued documents.
- Finish the full office/field workflow and live Moses SDK/web, Twilio A2P, and Resend tests separately. These are not certified by source-only unit tests.

## Safety

No production data or price settings are included in this ZIP. It does not delete, migrate or overwrite any PDS/SDC documents. Source-only tests cannot confirm live Twilio, Resend, QuickBooks, OpenAI, or browser/mobile workflows.
