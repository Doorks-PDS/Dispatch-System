DOORKS INTEGRATION CANDIDATE — STAGING ONLY — NOVEMBER BASELINE

This is a cumulative overlay of revisions 84–104 plus release-candidate contract tests.
It is NOT a production release, and it does NOT claim full three-role editor parity.

WHAT IS IMPLEMENTED
- Original office ticket remains the authoritative work-order editing workflow.
- Office and portal ticket presentations use the shared ticket field renderer.
- Office editor reuses shared ticket input controls for selected fields.
- Original office Estimate/Invoice builder remains the authoritative generator.
- Office and vendor document line items share row construction and totals logic.
- Customer has document preview and estimate response, not issuance access.
- Vendor has proposal line editing, not customer invoice issuance access.
- Customer/vendor operational requests go through office approval and manual application.

KNOWN GAPS — DO NOT CLAIM COMPLETE SHARED EDITOR
- Office and portal views still use different ticket shells.
- Vendor proposal editor is NOT the full office Estimate/Invoice editor.
- Operational approval does NOT automatically apply a change to the source record.
- Live browser, persistence, attachments, invoice numbering and authorization must be tested.

STAGING CHECKLIST (USE TEST ACCOUNTS AND TEST RECORDS ONLY)
[ ] Sign in as office_admin, confirm original dispatch tickets open/edit/save/reopen.
[ ] Create a test work order, attach files, add two completion forms, reload.
[ ] Generate a test estimate; verify tax, item lines, saved number, PDF and reopen.
[ ] Generate a test invoice; verify numbering and no accidental estimate overwrite.
[ ] Customer login: only own jobs; view ticket and estimate; send change request.
[ ] Vendor login: only assigned jobs; edit proposal; submit change request.
[ ] Office review: approve request, edit original job, mark applied, inspect audit.
[ ] Office review: reject with note, clarification with note, duplicate decision blocked.
[ ] Attempt direct portal API writes to office endpoints; verify 403/401.
[ ] Verify existing production records/data have NOT been modified.

SAFE INSTALL
1. Preserve November baseline; DO NOT deploy this ZIP on your live Render service.
2. Create a clean development branch from the actual November baseline.
3. Overlay the ZIP into the project root, excluding README from git if preferred.
4. Run: python -m pytest -q tests/test_doorks_rev*.py tests/test_doorks_candidate_integration.py
5. Run: node --check static/app.js && node --check static/doorks_shared_ticket.js
6. Deploy that branch to a SEPARATE Render staging service with separate data storage.
7. Perform the checklist; report failures with browser console and server logs.

NOTE: Some existing tests are static source-contract tests; 100% pass is not
proof of complete browser functionality. Treat the remaining integration gaps
as blockers for production, not as cosmetic follow-ups.
