# RecDebut registration inbox and family timeline — Record149 — 2026-10-27

Implemented private registration inbox with newest-first ordering, status filtering, revision-checked review saves, needs-information and duplicate decisions. Duplicate links preserve original receipts, families and contacts, reject invalid links/chains, and appear in both family histories. Family timeline provides saved changes, attributed internal notes, evidence snapshots and bounded pagination. Prior records remain intact; detailed history begins with this feature. Reviews and notes do not establish consent, payment, identity or sending authority.

52 focused backend tests passed (one existing Starlette deprecation warning). Real backend with isolated synthetic SQLite passed desktop1440 and phone390 browser checks: saved review survives reload, newest-first ordering, internal note persistence, dirty-navigation protection, no page exceptions or horizontal overflow. No synthetic production records created. Backend source compiles. Four frontend mirrors match. Whole-project TypeScript remains red on existing diagnostics; final output contains no diagnostics for changed RecDebut files. Retained initial harness failures, superseded first build, and all retry evidence; final browser check passed after correcting duplicate test-text selection.

Owned backend reloaded with fresh process identity and private online SQLite backup. Health, authenticated workflow access, unauthenticated denial, unconfigured intake503 and public legacy-registration hold passed; all prior row counts preserved. New backend PID36280 observed, rediscover before reuse. Six runtime activation controls remain false. Only the temporary synthetic browser backend was stopped after checks.

Firebase build web-v5-329-71-06f7bf5de34a deployed as Hosting version5c486005f1da8571. All191 live published asset hashes/version passed, prohibited files absent; 6629 module inputs rehashed current, recognized-secret hits0 and forbidden files0. Backend and local frontend source connected. Actual signed-in hosted editing and real website registration acceptance are not claimed. Retained Hosting rollback ebe02403917aea01, source originals and private database backup; do not discard later data on rollback.

Sending remains disabled pending Dennis/operator review. Website WordPress installation, exact form mapping, private signing-secret provisioning, public route and actual no-send/outage-recovery acceptance remain outstanding. No website administrator access, actual inbound website event, external message, payment or VM change. Cloud engineering-ledger synchronization pending.

User also supplied https://youtu.be/YJoPHIWmvnQ for potential distribution. Public page title observed: Recreational Debut PROMO. Saved as a review resource only; full audiovisual content, claims, permissions and intended audience have not been reviewed. No download, embedding change, campaign enrollment or distribution performed. Recommended later use: a reviewed link in an approved message or website placement after Dennis/operator approval; sending remains held.

## Verification and recovery evidence

Evidence: `backups/recdebut_inbox_20261027_record149`. Test command: `python -m pytest backend/tests/test_recdebut_workflow.py backend/tests/test_recdebut_registration.py backend/tests/test_recdebut_inbox.py -q`. Retained browser_release, vite_build_attempt2, firebase_deploy and hosting_verify command receipts, live_verification.json, rollback_plan_attempt2.json and backend_reload_receipt.json. Private backups/logs remain local.

## Measured source SHA-256

- `backend/recdebut_workflow.py`: `0ec197ba4979aeb7c3bfc09966f49455a1e452c0fcd34d834b62d90919d2dc33`
- `backend/tests/test_recdebut_inbox.py`: `aa2005889a0f69c129661a20d50d17125ed98937c996070a4e61990f7f92d158`
- `frontend/src/components/clients/RecDebutWorkspace.jsx`: `db01e5e8350fd202dc775c53bf8df7ca9024ed1c16d992e62ce240480944f354`
- `frontend/src/components/clients/RecDebutWorkspace.css`: `cb2db74b8418cea5c74131dcd40f89efd9488c5d1d28be759a986e65bf48e8da`
- `frontend/src/components/clients/RecDebutIntake.jsx`: `04d1628b17f0ea9b7c9d0ea466e6c3ee18189d1384675a55c72fa749318e8588`
