# Moses 5.79 — QuickBooks sync readiness (cumulative 5.72–5.79)

- New read-only `/pds-quickbooks/sync-readiness/invoices/{number}` and `/pds-quickbooks/sync-readiness/purchase-orders/{number}` routes, Office Admin only.
- Reuses 5.78 approved customer and service-vendor master links for prepared document identity review. Ambiguous/changed/unapproved identities never get a provider ID.
- Scopes identity hints to verified QuickBooks Online company and environment.
- Exposes remaining accounting checks, including item mappings, taxes, terms, and duplicate checks; never posts, imports, or sends payments.
- Adds eight offline tests for identity safety.

**Not implemented:** automated material supplier mapping, verified line-level item mapping, transactional posting, payment links, or automatic sync. This is a preliminary readiness view, not a green light to deploy.

**Important:** Cumulative patch requires committed Moses 5.71 on main. If local changes touch release files, the installer stops rather than overwrite. No runtime business JSON is included.
