# Moses 5.67 — Live AI diagnostics and PDS QuickBooks invoice handoff

**Basis:** GitHub `main` commit `530d6958b1973437e0879540a8b90baad5ea31e8` (Moses 5.66). This is a small, cumulative patch. No branches, services, production records, provider sends, API keys, or deployment are included.

## Moses and signed Resend webhook

- Reuses the existing Agents SDK, workspace permissions, hosted WebSearchTool, and approval/audit execution. Does **not** invent a second AI system.
- `GET /doorks-assistant/integration-health` (signed-in office admin) reports which Moses settings are missing, whether Resend's signed webhook secret is configured, and how many authenticated delivery events have been recorded. No credentials or customer data are disclosed.
- `/doorks-assistant/agent-web-check` remains the explicit hosted-tool verification. Its failure reasons now distinguish invalid OpenAI key, rate limit/quota, tool/model permission, network/timeout and unknown failure. It only counts an actual hosted search call as proof; the model saying it searched is not proof.
- Live web research and full agent execution remain **unverified** until Render's `OPENAI_API_KEY`, `DOORKS_MOSES_PDS_AGENT_ENABLED=true`, `DOORKS_MOSES_WEB_SEARCH_ENABLED=true`, and `MOSES_LIVE_VALIDATION_ENABLED=true` (for live diagnostics) are verified and configured **after deployment** where missing. The key must only be saved as a Render secret, never committed to GitHub.
- The existing Resend webhook endpoint is `/doorks-assistant/public/resend/webhook`. For delivery history it needs `RESEND_WEBHOOK_SECRET` configured from the Resend webhook; Resend delivery is not proven until a signed event is received. No auto-retry is added.

## PDS → QuickBooks initial bridge

Only **PDS saved invoices** are included, not supplier purchase orders or inventory. PDS and QuickBooks remain separate accounting ledgers until connection details and mappings are verified.

- `GET /pds-quickbooks/status` — read-only status/edition with no false connected claim.
- `GET /pds-quickbooks/invoices` — review candidate numbered JS invoices, totals, source job/customer link, saved PDF, Resend acceptance and exact approved PDF hash.
- `POST /pds-quickbooks/prepare-invoice` with `{ "invoice_number": "JS00021", "fingerprint": "<64-character hash>", "confirm": true }` — office admin explicitly stages one verified invoice, with duplicate protection, while making **no** external accounting entry.
- `GET /pds-quickbooks/review.csv` — downloads a review-only CSV of prepared invoices, not a QuickBooks-native import, and escapes spreadsheet formula cells.
- Queue state persists atomically on the Render disk (`pds_quickbooks_invoice_handoff.json`). Unsent invoices, unknown/changed PDFs, mismatched customers/jobs, corrupt ledgers, and repeat transfers of a changed invoice fail closed.
- Nothing automatically marks invoices paid, changes numbering, writes supplier bills/POs or changes inventory. No QuickBooks API credentials are used or required at this stage.

**Unresolved before real sync:** Which QuickBooks edition/version PDS actually runs. **QuickBooks Online** uses one-time Intuit OAuth 2.0 authorization and an API customer/item/tax mapping. **QuickBooks Desktop** uses the Windows QuickBooks Web Connector (QBWC) and qbXML with a running Desktop company file. It can auto-run when configured; no routine manual daily export is inherently required. This patch prepares the verified invoice outbox but deliberately does not pretend to implement a live Online/Desktop adapter without knowing which one is installed.

## Verification

- 8 new isolated unit tests passed for security, approval, idempotence, customer/job link validation, invoice total calculation, version hash consistency, safe Moses diagnostics and webhook status.
- Python compile checks pass. Existing modified files match the exact GitHub 5.66 file SHA and the patch is checked against those originals.
- Live OpenAI/tool check, Resend webhook delivery and QuickBooks integration are **not verified** and **not claimed**.

## After deployment

1. Open `/doorks-assistant/integration-health` in an authenticated PDS office-admin session. Configure any missing names in Render (NOT in GitHub). Setting environment values triggers Render deployment; do not do it ahead of the planned code rollout.
2. Run explicit web search validation from the authenticated app browser console: `fetch('/doorks-assistant/agent-web-check',{method:'POST',headers:{'x-moses-validation':'hosted-web-check'}}).then(r=>r.json()).then(console.log)`. Verify `web_search_verified: true` and then test a real Moses parts question.
3. In the Resend dashboard configure the signed event webhook to `https://dispatch-system-pl8q.onrender.com/doorks-assistant/public/resend/webhook` with relevant email delivery/bounce/delay events, save `RESEND_WEBHOOK_SECRET` in Render, and confirm an event count increase (no resend of uncertain emails until reconciled).
4. Confirm whether QuickBooks is **Online or Desktop** and its version, then wire that single adapter to the reviewed invoice queue. Configure customer/item/tax mappings and sandbox/company-file tests before any production post or auto-sync.
