# Vault consumer switch and rollback proposal

Later November21 scope note: this selector/generation map applies to lane A4-F
(Fernet store) only. Lanes A4-P (AES payload layer) and A4-K (plaintext vault_keys
credentials) are outside this model; see the parent migration plan and
../drafts/VAULT_TRACE_review_ClaudeCode.md. PROPOSED only; no switch occurred.

Later source160 update: publisher requires explicit encoding, pins both old and
candidate generations and authenticates compatibility before selector write.
14combined Windows checks pass; see ../agent_sync/VAULT_ADMISSION160_2026-11-14.md.
This supersedes the source159 integration-pending line for source admission only.
Live consumer inventory, actual decoding, interruption/review and switch remain open.

Later source159 update: pure explicit-encoding compatibility validator passes14
synthetic checks. Raw and balanced double-quoted Fernet occurrences preserve
authenticated values/timestamps and exact surrounding text/order. It is not yet
called by the publisher. Source158 separate-process competition/interruption14
also passed; earlier open-status lines below are retained baseline history. See
../agent_sync/VAULT_COMPATIBILITY159_2026-11-14.md. Live integration/inventory/
operator review remain open; no active switch occurred.

Later source158 update: cooperative byte-bound selector publication passes14
synthetic checks. Format/decryptability admission, competing/interrupted writers
and live integration remain open. See ../agent_sync/VAULT_PUBLICATION158_2026-11-14.md.
No active switch occurred.

Later source157 update: the opt-in read-only adapter now exists and passes14
synthetic Windows checks; see ../agent_sync/VAULT_READER157_2026-11-14.md.
Publication, format parsing and consumer hookup remain unimplemented. No live
selection or credential change. The following proposal retains its original156
baseline; qualified implementation scope is the later receipt only.

Status: PROPOSED; no implementation, new key, migration or activation. Source baseline5.329.156. This completes the concrete map requested after local preservation; it does not authorize the live transition.

The declared original key/config set is preserved privately and the recognized Fernet subset authenticated in a fresh process. Detailed field/occurrence maps, fingerprints and private paths remain in that protected set. Shared evidence is [the preservation report](../agent_sync/VAULT_PRIVATE_PRESERVATION_2026-11-14.md). Coverage remains the declared locations; other consumers, formats and loaded writers are not proven absent.

## Current contracts and proposed ownership

| Surface | Current behavior | Proposed change, still unimplemented |
|---|---|---|
| `backend/crypto_trader_bot.py` | Loads root then backend environment at import; later assignments override. Double quotes are stripped before raw Fernet detection. Backend key wins; root key is fallback only when backend key is absent. Failed decryption disables that value. | Resolve one immutable private bundle generation once per load, then load its matching key/config set. Preserve current parse/precedence semantics. A configured but invalid bundle fails closed; it never silently falls back to legacy paths or another generation. |
| `backend/Vault_Auto_Scanner.py` | Generates a missing key and rewrites backend environment in place, then scanner main can begin ingestion. | Separate explicit preservation/migration tooling from scanner startup. No missing-key generation or live in-place rewrite in the migration lane. Any later writer must stage a new generation and use the same admission/publication boundary. Never use scanner main as a migration test. |
| `backend/test_ccxt.py` | Can reach real credential-backed trading helpers. | Remains excluded from qualification. Use inert fixtures and then private-copy recovery, with all external account calls forbidden. |
| Other/imported consumers | Inventory incomplete; direct process-name absence does not prove inactivity. | Inventory and bind every affected consumer before activation. Preserve authorization and existing activation state; do not start trading or ingestion to demonstrate a switch. |
| Existing private-directory and atomic-file primitives | Already qualified elsewhere. | Reuse unchanged. No ACL takeover, recursive permission changes or replacement concurrency framework. |

Proposed implementation surfaces are a small `backend/security/vault_bundle.py` reader/admission adapter plus the two declared consumer integrations and separate migration tooling. These files are not created by this proposal. No new HTTP route or public path/key-selection API is proposed.

## Private generation layout and publication

Use a reviewed owner-private root, separate from repository/index/publication surfaces. Each immutable generation contains its own key, both configuration sources, original encoding/line-ending evidence and a private completeness manifest. A protected `current.json` selects only a validated generation identifier directly inside that root. It contains no key material. Reject absolute names, traversal, reparse redirects, incomplete/tampered generations and attempts to choose arbitrary private roots through a request body.

Generate and fsync every candidate file, verify the whole matching set, then publish only the selector using the existing same-volume atomic replacement primitive. Readers bind a generation before reading any member; publication must not mix a key from one generation with config from another. A generation identifier is not authorization. Manifest hashes identify bytes; they do not replace private permissions or Fernet authentication.

Current legacy consumers do not implement this selector. First adoption therefore needs a reviewed interruption window: determine all affected loaded readers/writers, quiesce only those approved, deploy the qualified adapter, configure the reviewed private root, and resume only previously enabled consumers. Changing a selector alone does not reload import-time credentials in an existing process. Record the generation actually loaded without logging keys or decrypted values.

## Exact format disposition

| Observed or possible format | Candidate treatment | Admission boundary |
|---|---|---|
| Authenticated raw Fernet token | Copy-first rotation with the supported library, preserving authenticated timestamp and plaintext identity. Retain old pair and candidate separately. | Every occurrence must authenticate under its mapped original key and then under the candidate key before publication. No new key is generated during this proposal. |
| Double-quoted Fernet | Preserve wrapper/reader semantics in a separately qualified case. The old scanner can double-encrypt this form. | Reject unsupported variants until their explicit fixture and private occurrence map pass; never treat a prefix check as authentication. |
| Single-quoted token, malformed token or unknown envelope | Retain original bytes and classify privately. | Reject automatic conversion or normalization. Do not retry with an unrelated key/provider. |
| Other nonempty or empty values | Copy existing bytes unchanged unless a separate field policy is reviewed. | Do not infer that a nonempty string is a valid credential or that every value should be encrypted during key rotation. Do not manufacture missing credentials. |
| Duplicate keys and root/backend overlap | Preserve source order and every occurrence, including overridden values. Use private file/occurrence identities rather than a dictionary that drops duplicates. | Compare the effective configuration under the actual reader semantics in private; do not print it. Changing precedence or cleaning duplicates is a separate change. |
| Encoding, comments and line endings | Preserve non-token bytes exactly. Establish actual runtime decoding before migration. | No incidental reformatting, newline conversion or guessed encoding correction. Unknown encoding rejects conversion. |

Actual mixed formats mean the earlier three-raw-token synthetic canary cannot serve as whole-store admission. Keep its12passing checks unchanged. Add only the missing format/selector cases when implementing the adapter; bind private checks to the exact preserved generation.

## Switch, rejection and rollback

1. Revalidate the private preservation receipt and exact current source/store generation. If originals changed, retain the existing snapshot and create a separate fresh set; never overwrite it.
2. Complete consumer/writer inventory and private per-occurrence format map. Resolve unsupported cases before staging. Prepare the exact interruption/resume list for operator review.
3. Qualify the new reader/selector and copy-first writer in synthetic private roots: invalid selector, redirection, mixed generation, interrupted publication, stale source and concurrent writer rejection must remain inspectable.
4. After operator approval, stage a new private generation. Keep original key/config and rollback selection intact. No credential changes or live publication are performed by saving this map.
5. Verify candidate file identity/counts, every transformed token, preserved non-token bytes and effective reader output privately. Record only sanitized outcomes outside private storage.
6. During the reviewed window, quiesce affected writers/readers and revalidate source generation before publication. Reject on drift; do not force an apply.
7. Publish the single selector, then qualify each approved consumer's actual loaded generation and lifecycle without external trading/ingestion side effects. Unknown outcome prevents automatic retry.
8. For adapter-to-adapter rollback, reselect the preserved qualified old generation and reload the affected approved consumers. Retain the failed generation and diagnostics.
9. For first-adoption rollback to legacy code, stop the affected consumers, restore their earlier code/config selection, and resume only the previous activation state against the untouched original paths. Do not perform a two-file live overwrite and call it atomic rollback.
10. Retain recovery material through an explicitly agreed window. Repository untracking/history/remotes/clones remediation is a separate reviewed operation; neither a selector nor a new key removes earlier copies.

## Required evidence before live approval

- Complete affected consumer/writer and private format/occurrence inventories; unknown scope is a stop condition for activation, not permission to assume absence.
- Exact owner-private preservation/readback and source-generation identities, with all credentials and fingerprints retained privately.
- New selector/format/interruption/stale-generation and rollback qualification; no reuse of unrelated green checks as proof.
- A concrete interruption/resume list, named reviewer and explicit decision receipt required by the parent migration plan.
- Separate receipts for candidate transformation, live consumer switch, rollback availability and repository/history remediation.

Current disposition: the declared original pair is preserved and recognized private recovery passed. The adapter, writer admission, exhaustive inventory, new-format/selector checks and live operator decision are not complete. No application version bump, consumer restart, key generation, migration, repository change or private upload occurred while writing this proposal. Continue independent AI-BS acceptance work while live migration stays behind this review boundary.
