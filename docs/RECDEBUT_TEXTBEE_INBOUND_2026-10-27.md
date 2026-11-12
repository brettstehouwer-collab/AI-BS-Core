# RecDebut durable TextBee intake and STOP suppression - Record154

Repaired authenticated TextBee reply intake independently of outbound activation. Strict flat MESSAGE_RECEIVED validation, bounded raw-body HMAC on every alias (including administrator requests), atomic reply/suppression/receipt storage, canonical event identity, duplicate/replay conflict handling and retryable storage failures are implemented. STOP/STOPALL/UNSUBSCRIBE/CANCEL/END/QUIT/REVOKE/OPT OUT persist common suppression before optional CRM classification. Unknown or personal senders remain excluded from the recruiting reply inbox; START does not remove suppression or grant consent. Optional contact/JSON/inbox failures cannot discard an authenticated opt-out. No automatic reply or acknowledgment SMS.

101 focused offline tests passed with one existing Starlette TestClient deprecation warning. Synthetic SQLite/FastAPI checks cover all three routes, signatures, limits, replay/concurrency, transaction rollback/retry, malformed contact records, family timeline and preview invalidation. Five Python sources compiled; all unrelated router AST nodes unchanged; recognized secret signatures in additions zero. Initial red tests and first green-attempt harness failures retained and corrected; no failure evidence removed. These are trusted-controller tests, not provider delivery or VM containment acceptance.

Controlled owned-backend reload passed fresh executable/creation/owner identity checks and retained a private online SQLite backup. Health and authenticated workflow access passed; unsigned administrator webhook calls returned401 and signed malformed events400 on all three aliases, without inserting production events. Existing row counts preserved, SQLite quick_check passed, configuration and outbound policy unchanged, other services preserved, six activation controlsfalse and8888off. Observed backendPID40992 is historical evidence only; rediscover before reuse. No frontend change or Firebase release for this TextBee checkpoint.

Sending remains disabled pending Dennis/operator review. No SMS/email sent, polling enabled, provider subscription/settings changed, historical replies replayed, valid production events injected or VM operation. Actual provider-to-public-webhook/reply acceptance remains unverified. Legacy dispatch selectors still need shared suppression enforcement and reviewed exact sender, audience/permission, message, limits, reservations and unknown-outcome retry controls before any later activation. Website registration is still intentionally unconfigured/held. Cloud ledger synchronization pending.

## Evidence

`backups/recdebut_textbee_inbound_20261027`: tests_release.txt (101 passed), preflight.json, backend_reload_receipt.json, original sources/docs and retained failed attempts. Private backup/logs stay local. Test command: `python -m pytest backend/tests/test_recdebut_workflow.py backend/tests/test_recdebut_registration.py backend/tests/test_recdebut_inbox.py backend/tests/test_recdebut_textbee.py -q` with a unique basetemp.

Official provider schema/HMAC reference reviewed: https://textbee.dev/docs/webhooks . Actual provider event remains a separate acceptance step.

## Measured source SHA-256

- `backend/recdebut_textbee.py`: `b986386f1e80dccd93d9f28b5b162718b4e5737e5dba622aedcf4dd573171441`
- `backend/recdebut_workflow.py`: `a79941389243e9497344d2b1e22496981b8db22a146c4739470cd7fcd4640d43`
- `backend/security/recdebut_access.py`: `6a4a4cea2a8e5e93f8d7f5b0bc342248b514e6ed9abdb604db9f8636424b8bed`
- `backend/routers/rec_debut_router.py`: `87ad2da2e501e71f5182bf32cbf4498a9e964d92b6887494976909ee4dae691f`
- `backend/tests/test_recdebut_textbee.py`: `b56225a330c6397d764f2c92d5ee7dda9d13fab973bc8c747466b8cbe64f4a15`
