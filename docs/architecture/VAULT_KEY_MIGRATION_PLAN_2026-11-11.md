# Vault-key preservation and migration plan

## Scope extension: AES payload and plaintext credential lanes — November21,2026

Status: PROPOSED — NOT APPLIED; each phase needs owner approval. This plan, the
switch proposal and VAULT_KEY_CONSUMERS_2026-11-11.json cover only the Fernet
store (lane A4-F). The consumer JSON remains Fernet-only. backend/vault_master.key
is tracked in the current index and present in origin/main; treat it as exposed.
Lane A4-P: backend/core/cryptographic_vault.py AES-GCM payload layer. Default
passphrase/salt are public and the legacy key is always accepted. Backend
/api/security/decrypt (AI_BS_Backend.py:3571) has no admin boundary. rawFallback
plaintext substitution (:9062-9068, :14461-14471) means retained legacy envelopes
already carry plaintext: mainly code fix/retirement, not re-encryption.
Lane A4-K: backend/modules/vault_router.py:86,93,100,107 hardcoded credentials,
public in origin/main, seeded as plaintext into vault_keys (:113-118, :124).
Owner revocation first, then seed removal and reviewed row cleanup on an isolated
copy. Never use the Fernet key for A4-P or A4-K. Findings, phases and acceptance:
docs/drafts/VAULT_TRACE_review_ClaudeCode.md. Issue separate receipts per lane,
consistent with step 9. No code, data, credential or service change occurred.

## Concrete switch/rollback map — November14,2026

The proposed immutable-generation/single-selector consumer and rollback map is
now written in VAULT_CONSUMER_SWITCH_PROPOSAL_2026-11-14.md and JSON companion.
It binds actual legacy precedence, mixed formats and first-adoption constraints.
No adapter or live transition exists. Next source-only opt-in reader/admission
with synthetic checks; active changes remain behind the operator review below.

## Local private preservation and recognized recovery — November14,2026

Original declared key/environment files are now privately preserved byte-for-byte.
A fresh process verified copies and authenticated the recognized Fernet subset;
decrypted outputs were not persisted/logged. Actual config retains its original
mixed formats. Active files/keys/consumers remain unchanged. No whole-vault,
all-writer or transactional multi-file snapshot claim. See
docs/agent_sync/VAULT_PRIVATE_PRESERVATION_2026-11-14.md. Next concrete proposed
consumer switch/rollback map; parent operator-review boundary still applies before
any real switch/credential change. Private files never enter the shared archive.

## Actual declared-store preflight — November14,2026

Read-only metadata/aggregate variant classification is now recorded in
docs/agent_sync/VAULT_ACTUAL_PREFLIGHT_2026-11-14.md. Actual configuration has
mixed value formats and duplicate/override behavior; the earlier raw-token
canary cannot be applied blindly. No key bytes read, private recovery/copy or
migration performed. Detailed local inventory is excluded from shared backup.
Next review the existing owner-private helper/destination and preserve original
key/config locally before checking recoverability. Existing migration/switch/
history boundaries below remain in force.

Status: LOCAL ORIGINAL PAIR PRESERVED; RECOGNIZED PRIVATE RECOVERY PASS; ACTIVE MIGRATION NOT EXECUTED. Added to the active ten-goal program November11,2026. Original planning and synthetic canary did not read real keys. Later local preservation copied original bytes and authenticated recognized values from private copies, without logging/uploading key or decrypted material. Active keys/consumers remain unchanged.

## Confirmed evidence and limits

`backend/vault_master.key` is currently tracked and its path appears in three reachable commits. An existing ignore entry does not untrack it or remove history. Read-only references were found in `backend/crypto_trader_bot.py` and `backend/Vault_Auto_Scanner.py`; this is not yet a complete encrypted-consumer inventory. Git tracking proves repository exposure potential, not public disclosure. Current document ownership, private stores and encrypted data must remain intact.

## Required sequence

1. Inventory key consumers, ciphertext locations, envelope/algorithm versions, key lookup precedence and any running writer using code/configuration metadata. Do not print secrets or decrypt private records into shared outputs. Identify whether any other data or services use the same material.
2. Prepare an owner-private preservation set of original encrypted data, original key and consumer configuration under the existing separate private-data preservation rules. This is not an engineering-source upload. Verify recoverability in an isolated private location before touching the active key. Record counts and receipts without publishing key material.
3. Produce a concrete migration map and rollback procedure for each actual format. Establish a synthetic canary matching each real schema; prove old-reader/new-reader behavior and interrupted-write recovery. Decide whether versioned key IDs/envelopes are needed; do not assume one file replacement migrates ciphertext.
4. Review the exact affected stores and interruption window with the operator before performing credential changes or pausing active writers. Existing development preapproval is not permission to discard encryption access or upload a private key. Do not start trading, scanners or unrelated business processes to test migration.
5. Generate replacement material through the approved local secret mechanism, never in a source file, command line, chat or engineering archive. Migrate copy-first into a new private destination, with bounded transactional batches and no destructive overwrite of the preserved original set.
6. Verify record counts, authenticated decryptability and representative private readback locally. Never write plaintext private contents into shared logs. Test restart, interrupted-batch continuation and rollback before switching consumer configuration.
7. Switch only verified consumers; retain original recovery access for the agreed rollback window. A failure must preserve both original ciphertext and original key. Keep original document owners and activation flags unchanged.
8. Separately remove the key from future source snapshots/index and resolve reachable history/remotes/clones with an explicitly scoped repository-history plan. Do not rewrite branches, delete backups or assume ignore rules repair existing history. A history rewrite does not revoke leaked material; a key replacement does not remove old copies.
9. Issue separate receipts for data migration, consumer switch, repository remediation and private backup verification. Never call the operation complete from an ignore-file change alone.

## Acceptance

- Complete consumer/ciphertext inventory and migration/rollback map reviewed.
- Preserved original key/ciphertext recovery proven privately; no secret appears in shared artifacts.
- Synthetic format, interruption, new-reader and rollback tests pass.
- Actual encrypted record counts and private readback pass after a controlled switch.
- Running consumers use the intended key source and retain prior authorization/activation settings.
- Future source snapshots exclude keys; reachable history and remote exposure are explicitly resolved or recorded as an open gap.
- Data-preservation and engineering-source backup coverage remain separate.

The scoped source-only consumer/format inventory is now recorded in `VAULT_KEY_CONSUMERS_2026-11-11.json`. It identifies the Fernet reader, missing-key-generating writer, import-time environment precedence and a live credential test to avoid. Private keys/ciphertext/record counts/decryptability/ACLs/running writers remain unverified.

Inert format/canary and controlled interruption/restart/rollback checks now pass12/12. Read `VAULT_SYNTHETIC_CANARY_2026-11-14.md` for the exact source fingerprints, format/switch map, quoted-token hazard and limitations. The synthetic rehearsal can precede private preservation because it uses no real store. It does not qualify real encrypted counts, private recovery, coherent consumer switching or power-loss durability.

Next action: prepare the separately governed private preservation inventory and exact affected-store review before any real migration. No key rotation, untracking, history rewrite or data migration is authorized by this plan's existence.
