# Moses 5.75 — QuickBooks document-number duplicate preflight

## Cumulative installer / baseline

Includes **5.72 + 5.73 + 5.74 + 5.75** for the committed Moses 5.71 `main` baseline (`d6d71ff2e56983d2d8461f5d0a67d228fc4183e9`). **Do not install 5.72–5.74 separately** when using this cumulative ZIP. Does not deploy to Render or authorize live QuickBooks posting.

## New in 5.75

- Office Admin can check an already prepared, unchanged PDS invoice or supplier purchase order against the verified QuickBooks Online company for **exact DocNumber collisions**, using a bounded **GET** query. It is surfaced in QuickBooks Hub > Connection setup.
- Reports only provider transaction IDs, document numbers and sync tokens. No customer contact, banking, token or financial details are exposed.
- Invalid numbers, stale/unprepared sources, absent/mismatched company verification and non-admin roles fail closed.
- A `no match` result is **not** a green light to post. Customer/vendor/item/tax mapping, manual reconciliation, provider-side idempotency and controlled end-to-end testing are still required.
- No QuickBooks invoice, supplier PO, supplier bill, payment, payment link or account transfer is created by this revision.

## Retained from 5.72–5.74

- Multiple To/CC recipients for PDS estimate/invoice email, saved customer contact suggestions, guarded Resend workflow.
- Recommendation / Completion **Save & Estimate** from the saved source form; original **Ready to Quote** retained.
- Leads/technicians: view existing supplier POs only; Office and Office Admin manage; Office Admin deletion.
- Invoice/PO QuickBooks handoff previews and numbering policy; Intuit OAuth with encrypted persistent storage; read-only company verification and provider catalog.
- Proposed **0.5% service fee** is a *preview*, not charged or transferred to SDC.

## Still inactive

Provider posting, automatic sync, payment links, reconciliation writes and SDC fee transfers. Verify the QBO edition/account, authorization, mappings, payment processor and fee treatment before activating any of those.

## Testing limitations

The uploaded source archive lacks the local `scripts/` folder used by six test collection modules and two smoke tests. These are run by the installer against the user's complete checkout. The single known supplier-part fixture failure exists on the previous baseline and is explicitly deselected by the installer.
