# Moses 5.68 — PDS QuickBooks Hub (Office Admin only)

**Cumulative basis:** GitHub `main` commit `530d6958b1973437e0879540a8b90baad5ea31e8` (Moses 5.66). This cumulative ZIP includes **both 5.67 and 5.68**, in one patch. Do not separately install 5.67 beforehand.

## QuickBooks Hub

- PDS **Office Flow → QuickBooks Hub** appears immediately below Accounting Hub. Not a new Accounting Hub card or a separate service.
- The Office Admin role is the **only** role allowed to see the sidebar entry or load any `/pds-quickbooks/*` API response. Backend protection applies to status, invoices, staging, CSV export and setup even when the endpoint URL is requested directly. No permissions are granted to ordinary Office users, Leads or Technicians.
- Dashboard with clean cards for **Ready**, **Prepared**, **Needs attention** and **Connection state**; searchable/filtered invoice list; **Invoices**, **Activity** and **Setup** tabs. Mobile-responsive styles are contained in `static/pds_quickbooks_hub.css`.
- Administrator can select QuickBooks **Online** or **Desktop**, explicitly confirm, and save only the edition on the existing persistent PDS data disk as `pds_quickbooks_settings.json`. The setting is not a credential, does not authorize a QuickBooks account and does not enable syncing. If `PDS_QUICKBOOKS_EDITION` is already defined in Render, it remains authoritative and the UI will not override it.
- Existing 5.67 invoice-review queue is the only available preparation workflow. Save does **not** send an invoice to QuickBooks. The CSV is a review file, not a QuickBooks-native import. It does not touch inventory, purchases, payments or accounting ledgers.
- Staging is confirmation-backed and idempotent. Only issued, job/customer/PDF-hash-verified invoices are prepared. Mismatches require review, and repeat preparation of an altered invoice is refused.
- No automatic posting, polling, duplicate creation, customer mapping or QuickBooks OAuth / Web Connector setup is claimed. Those require identifying PDS's actual QuickBooks edition and later authorization.

## Also carried forward from unapplied 5.67

- Moses AI and web-search readiness diagnostics with specific configuration errors, without leaking keys.
- Existing Resend webhook readiness (no new webhook service) and signed delivery-history checks.
- Verified issued-invoice handoff and safe review CSV, with a durable queue and duplicate protection.
- The pre-existing HTTP readiness test was adjusted to allow the **name** `OPENAI_API_KEY` in a missing-configuration list, while prohibiting a displayed credential-value assignment.

## Testing

- **996 passed, 2 skipped** on the reconstructed project with the GitHub `moses_preflight.py` helper restored for tests (the helper is already in GitHub and is **not** included as a replacement in the patch).
- `node --check static/app.js` and Python compile checks pass.
- The cumulative patch has been checked for clean application to the reconstructed 5.66 GitHub source.
- Live QuickBooks, Moses hosted web search, Resend webhook delivery and browser acceptance are **not** verified by the unit tests. No GitHub push, Render change, deployment, bank or accounting entry or customer send was performed.

## After later deployment

1. Office Admin opens **QuickBooks Hub** under Accounting Hub, selects Online or Desktop, and saves the choice.
2. Admin reviews invoice eligibility; approved issuance alone is insufficient unless the exact saved PDF matches the Resend-accepted copy.
3. Use **Prepare handoff** and **Export review CSV** for manual accounting review. **No sync takes place yet.**
4. When the edition is confirmed, implement and test its corresponding connector (Online OAuth 2.0 API or Desktop Web Connector) before enabling automatic synchronization.
5. Run the Moses and Resend live diagnostics from 5.67 once Render secrets have been configured in the existing service; never commit API keys to GitHub.
