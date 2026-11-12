# Record148 — RecDebut registration receiver preparation — 2026-10-27

Prepared dedicated signed registration intake that atomically creates private family/contact/review-task records and audit events. HMAC binds exact body and bounded timestamp; 16KiB streamed limit, strict schema, exact form allowlist, event idempotency and changed-event conflict. Contact permissions and guardian relationships remain unknown. No provider calls, endorsements, payments or sending authority. Public legacy registration remains503.
45 synthetic tests passed (one existing TestClient deprecation warning); four changed runtime sources compile. Synthetic checks include actual access-helper middleware/dependency chain, retries, tampering, stale/future requests, missing configuration, form exclusion, rollback on invalid data, shared guardian separation and size bounds. No real website form submitted. Public WordPress/Elementor field observations are provisional; no administrator access and no plugin installed. Operator confirmed website access unavailable. Documented server-only connection contract, limited field mapping, website notification review and durable outbox requirements. New user-supplied outreach report retained as historical claims; active/delivered/human/consent assertions not adopted and credential fragments/private recipients excluded.
Owned backend reloaded after fresh process identity validation, private online SQLite backup and before/after source hashes. Health, authenticated workflow read, unauthenticated denial, intake unconfigured503 and legacy registration hold passed. All existing table row counts unchanged; six process controls false, loopback8080 preserved. New PID50804 observed; rediscover before reuse. No runtime registration secret or forms provisioned. No frontend changes or Firebase redeployment: existing Record147 dashboard remains in place and receives future accepted records through its existing workflow API.
Live website connection BLOCKED on website administrator installation/review, verified HTTPS route, private signing-secret provisioning, actual form identities and end-to-end/no-send/outbox-recovery acceptance. The local receiver is deployed but intentionally unconfigured; no actual website registration accepted. Sending remains disabled pending Dennis/operator review. No VM changes. Cloud ledger synchronization pending.

Evidence: backups/recdebut_registration_20261027_record148. Installation contract: docs/RECDEBUT_WEBSITE_CONNECTION.md.

## Measured source SHA-256

- `backend/recdebut_registration.py`: `4258faf707c66d2ae2ab5d7729ac2e84759f70f70cc73772a3a2242680028129`
- `backend/security/recdebut_registration_auth.py`: `426809abc6fe743aafeaf90610e520399b340bba63a91be7e2cef5c637752fb0`
- `backend/security/recdebut_access.py`: `04821b4e936140076c33cff096ac26f8cbf6c929092b761745e6f7488ab131cb`
- `backend/routers/rec_debut_router.py`: `5a29b27942a6cc972081f3f3627fdfccdb6ea59e036f3f7383cb973aceaec10f`
- `backend/tests/test_recdebut_registration.py`: `08fc1f9ba3194b3bdc0572d71fe0bb83ded295cd69ce69ec46d620ec6260dbd5`
- `docs/RECDEBUT_WEBSITE_CONNECTION.md`: `05112512250b5ec3941ea2e84d9b4b90b2516ab323e8a6fd0dc0235b0fc97581`

Validation commands: `python -m pytest backend/tests/test_recdebut_registration.py backend/tests/test_recdebut_workflow.py -q`; `python -m py_compile` on the four changed runtime sources; retained controlled reload script and boolean-only health/auth/hold receipt. No synthetic contacts written to the production database. Private logs/database backup stay local.
