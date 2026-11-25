# Moses 5.80 — Purchasing supplier master links (cumulative 5.72–5.80)

- Adds **PDS purchasing suppliers** as a separate QuickBooks master mapping category from service vendors.
- Existing supplier profiles are read from `data/pds_suppliers/records.json` without creating, importing, or modifying records.
- Office Admin can view and explicitly approve an active matching QuickBooks Vendor ID through the same provider-verification and audit-ledger controls introduced in 5.78.
- Prepared supplier PO readiness now checks the saved supplier profile ID (if present) along with the vendor name. An unknown/stale/mismatched ID is blocked; legacy no-ID POs remain ambiguous until reviewed.
- Adds ten offline supplier identity tests, including company mismatch, duplicate display names, tampered records, and source isolation.
- No QuickBooks writes, invoice or PO posting, payment links, transfers, or automatic synchronization are enabled. The universal 0.5% service fee remains preview-only.

The cumulative patch applies to committed Moses 5.71 on `main`. Release installer protects unrelated local changes. Production deployment remains on hold pending full local and live checks.
