# Vault preservation canary — synthetic evidence only

Status: **SYNTHETIC_CANARY_12_PASS; PRIVATE_PRESERVATION_AND_MIGRATION_OPEN**.
Evidence: `backups/vault_canary_20261114_v01/result.json`, using recovery Python
3.12.14 and cryptography49.0.0. Source remains149; no application source changed.

Only the reviewed `decrypt_vault_key` and `encrypt_env_keys` function ASTs were
compiled into fixture-bound namespaces. The trading/scanner modules were never
imported, their main/startup bodies were not executed, and file opens in those
functions were restricted to the owned synthetic fixture. This is a fixture
boundary, not a same-account security sandbox. No real key, environment file,
ciphertext, credential-backed test, writer or business operation was accessed.

The12 checks establish actual legacy writer/reader compatibility on three raw
Fernet records; exact retry bytes; backend/root key precedence; inability of key
replacement alone to migrate old tokens; copy-first rotation preserving content
and authenticated token timestamps; a controlled interrupted child leaving the
old pair intact; fresh-process rejection of incomplete/tampered staging; fresh
staging and verification; and exact original-pair rollback/readability.
Expected negative child exits23/24 are recorded rejection/interruption evidence.
They are not hidden successes or unexpected runtime failures.

The actual legacy writer double-encrypts quoted Fernet tokens. The experiment
reproduces that hazard without fixing the production writer. Its proposed
canary admission refuses quoted/duplicate/incomplete records, rather than
claiming normalization is safe. Root/backend precedence also remains unchanged;
the live effective-key and duplicate/environment-value inventory is still open.

## Concrete format and rollback decisions

| Surface | Decision supported by this rehearsal | Required before private use |
|---|---|---|
| Current raw Fernet values | Rotation can retain raw-token format and timestamp; no new crypto envelope is required merely to re-encrypt a token | Map every actual consumer, token variant, encoding, quote and owner; do not apply the three-field fixture parser to unknown data |
| Current reader | A consistent old pair and consistent new pair are independently readable with the unchanged algorithm | Existing hard-coded paths do not provide a versioned bundle selector; design/review a coherent consumer switch or a controlled writer/reader stop window |
| Key/ciphertext coupling | A replacement key alone cannot recover old tokens | Preserve both original keys and all ciphertext/configuration before any replacement; never generate a missing live key as a migration shortcut |
| Staging | Keep new key and re-encrypted data in a separate private destination; validate completeness and every token before admission | Define private permissions, manifests, counts, source generation and all real formats; no in-place scanner rewrite |
| Interruption/restart | Incomplete output rejects; the preserved source remains readable; fresh staging can rebuild a verified candidate | Qualify real batch/journal recovery and storage failure behavior; this controlled child exit is not sudden power-loss or filesystem durability evidence |
| Rollback | Re-select or restore the preserved original pair together, then verify original reads/counts | Qualify actual private recoverability and consumer authority before switching; retain recovery access for the reviewed rollback window |

The canary uses the library's [Fernet/MultiFernet rotation API](https://cryptography.io/en/latest/fernet/).
The consulted current documentation is51development; all exercised operations
were actually verified on installed49.0.0, and no51-only feature is required.
No custom encryption primitive or production migration tool was introduced.

The source/evidence archive is explicitly allowlisted: script, redacted counts/
statuses, function snippets, source fingerprints, plan/map and child logs. All
fixture keys, ciphertext/environment files, plaintext fixtures and private
stores are excluded. Even synthetic key material is not uploaded.

Next is the separately governed private preservation inventory and exact-store
review from the parent plan. Live migration, key rotation, consumer activation,
Git untracking/history rewriting and trading/scanner startup remain unexecuted.

Backup outcome: the21member source/evidence archive uploaded as
`1PPZcFjqLN50es6aaXL3vAWPRoG2mMWQi`, but Drive blocked download with403 and a
malware/spam classification. No source roundtrip verification or bypass is
claimed. A separate non-executable checkpoint report `1nhy_IE7NGY7041_roGtOcX1JmiarcurQ`
was downloaded and hash-verified:1746bytes/SHA
`c68baa011670807a6845c494ca1fb5edf769d348ac9b985280821e379fb47ed0`.
This report-only backup does not substitute for source/private-store recovery.
Both outcomes and the local source archive remain preserved.
