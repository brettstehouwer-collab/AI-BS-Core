# Vault-key preservation and migration plan

Status: PLANNED / NOT EXECUTED. Added to the active ten-goal program by the user on November 11, 2026. No key value was read, exported, changed or removed during the review.

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

Next action: design inert format/canary and interrupted-migration/rollback checks, then prepare the separately governed private preservation step. No key rotation, untracking, history rewrite or data migration is authorized by this plan's existence.
