# Vault trace review and A4 reconciliation

This is Claude Code. Draft dated 2026-11-21, written under the owner's scope assignment (vault-plan reconciliation, documentation only). Status: **PROPOSED — NOT APPLIED.** No code, database, environment file, credential, service, repository visibility or deployment was changed. No application code ran. No secret value appears in this file; credential locations are given by path and line only.

## Baseline

Checkout `C:\AI-BS`, branch `codex/audit-v532976-20261031`, HEAD `64fad2871e0a716d9964f506bdef1050612b173d`. Line numbers refer to the working tree fingerprinted at 2026-11-21T20:06Z:

| Path | SHA-256 |
| --- | --- |
| backend/core/cryptographic_vault.py (untracked, ignored by `*crypto*`) | 38622fe44c2632934308d7fb07a2d1c93a8019b0f391d40ff1739f942e4573b0 |
| backend/modules/vault_router.py (tracked, equal to HEAD) | aa4fe455558e91f2d67b156bf9b09e621346e869d9f453723d0510ec8c034709 |
| backend/AI_BS_Backend.py | c226980d87ce4462057f34537080793c84afea03d53e4ee7d82730a80c2e4c26 |
| backend/security/vault_access.py | a2c610eac6626b5e4a4d2a99ac011e8eb6660ead445c415e3dd9650d2c9b9f1d |
| backend/test_aes_e2e_encryption.py | 4bf4c5224417bf9475d57e73305791404ecebc86efd8d9838138f919ab44400a |
| frontend/src/security.js (all five copies identical) | abbca7fbe6c8841ef4006281bf41989147a79f1e1eb4fe8afd8ffc8f148d4fdf |
| frontend/vault_old/App_v1.4.1.jsx | 5b317a4c83f0f0caf647fffd492cd7c3ddef03f21c90e780f6bd0e09018cbc35 |
| docs/drafts/VAULT_TRACE_Codex.md (reviewed document) | d098b76cde793849801b452ec073433a2580097f4b4343978868d9cb9ecb366d |
| docs/architecture/VAULT_KEY_MIGRATION_PLAN_2026-11-11.md | e7036986ce3fb699c4183fa009e85f6559a6d0d6e7416c878d6f275672c5e298 |
| docs/architecture/VAULT_CONSUMER_SWITCH_PROPOSAL_2026-11-14.md | 9616aa099cc46104ebaecc5c5ab19ebb9a436ed9299c8563fabd8b59ccf661e4 |

Git blob comparison (no contents printed): `frontend/src/security.js`, `frontend/components/security.js` and `frontend/vault_old/App_v1.4.1.jsx` are byte-identical to `origin/main`. The four long credential literals in `backend/modules/vault_router.py` hash-match the `origin/main` copy (4 of 4).

## 1. Verification of VAULT_TRACE_Codex.md

| Trace claim | Result |
| --- | --- |
| §1 load order: `AI_BS_Backend.py:222` imports `modules.vault_router`; `vault_router.py:37,62–65,124` runs `load_dotenv` on `backend/.env` at import; vault import at `AI_BS_Backend.py:3309`; vault selects inputs at `cryptographic_vault.py:65–75`, singleton at 130–132 | VERIFIED |
| §2 decrypt sites `AI_BS_Backend.py:3571–3589`, `9027–9031/9054–9060`, `14427–14459` | VERIFIED (see H2 for an omission at the same sites) |
| §2 only two Python importers (backend entry and `test_aes_e2e_encryption.py:26`) | VERIFIED |
| §2 rotation updates process memory only; no key-version column or migration step | VERIFIED (see M1 for an omission) |
| §3 five identical browser helpers; declarations L4–9, derive L37, import L72, encrypt L88, decrypt L115 | VERIFIED |
| §3 `vault_old/App_v1.4.1.jsx:12,311–325` sends an encrypted chat envelope | PARTLY VERIFIED: the send spans L310–328+ and carries plaintext copies (H2) |
| §2 test ranges `61–217, 220–272` | Minor drift: HTTP cases are `test_07` L220–248 and `test_08` L249–281 |
| §4 public-source exposure of default derivation inputs and legacy key | VERIFIED by blob identity with `origin/main` |
| §5 legacy ciphertext existence unknown | Holds; H2 changes what a retained legacy request means |
| §6 migration order | Sound in outline; reconciled below |

## 2. Findings

### Critical

**C1. Hardcoded third-party credentials in public source, missing from the trace and from ORIGIN_EXPOSURE_Codex.md.** `backend/modules/vault_router.py:86` (RapidAPI), `:93` (Gemini), `:100` (Crypto.com API key identifier), `:107` (Discord bot token). The file is tracked and present in `origin/main` with the same values. At import (`:113–118`, `:124`) they are written as plaintext into `vault_keys.apiKey` with `INSERT OR IGNORE`, so copies persist in `backend/aibs_master.db` or `backend/stehouwer_vault.db` (whichever `:17–22` selects) independently of later source edits. The AES vault never protects these rows. The ORIGIN_EXPOSURE heuristic matched quoted *assignments*; these are tuple elements, so they were missed.

**C2. Public fallback key and always-accepted legacy key.** Built-in default passphrase and salt (`cryptographic_vault.py:22–23`, used at `:65–70`) and the fixed legacy key (`:19`) are reproduced in the five browser helpers, which are public in `origin/main`. Any process that starts without both `backend/.env` values derives a publicly known key. The legacy key is accepted on every decrypt failure (`:122–124`), regardless of configuration.

### High

**H1. Unauthenticated decrypt endpoint.** `/api/security/decrypt` (`AI_BS_Backend.py:3571–3589`) is not covered by `AdminExecutionBoundaryMiddleware.SENSITIVE_PREFIXES` (`:1828–1849`; only `/api/security/backups` at `:1836`) or by `vault_access.PREFIXES` (`vault_access.py:9–13`). At the backend layer it decrypts arbitrary input and returns plaintext. `test_aes_e2e_encryption.py` (`test_07`, L224–226) asserts HTTP 200 without credentials. Gateway-level protection on port 8000 is UNVERIFIED.

**H2. `rawFallback` plaintext bypass.** On decrypt failure the server substitutes the client-supplied plaintext `rawFallback` object (`AI_BS_Backend.py:9062–9068`, `14461–14471`). The archived sender (`vault_old/App_v1.4.1.jsx:322–328`) includes the same plaintext in `rawFallback` and `messages` beside the ciphertext. The envelope therefore provided neither confidentiality nor integrity. Any retained legacy request already contains its plaintext.

### Medium

- **M1. Stale aliases after rotation.** `rotate_key` (`cryptographic_vault.py:77–86`) updates only the instance; module aliases `aesgcm` and `AES_SECRET_KEY` (`:131–132`), imported at `AI_BS_Backend.py:3313–3315`, keep the import-time key. `get_active_key` (`:88–89`) exports raw key bytes.
- **M2. Legacy fallback with caller-supplied key.** When a caller passes `key`, failure still retries the legacy key (`:116–124`).
- **M3. No envelope version, key identifier or associated data** (`:101`, `:120`). A future migration cannot tell which key produced a record.

### Low

- **L1.** Error text from the exception is returned to the client (`AI_BS_Backend.py:3587`) and printed (`:9064`, `:14465`).
- **L2.** `test_08` accepts 200/500/503, but `/api/chat` is admin-gated (`:1830`), so an unauthenticated run would likely receive 403. Not executed.
- **L3.** Trace line-range drift noted in section 1.

## 3. Reconciliation with A4 (VAULT_KEY_MIGRATION_PLAN and CONSUMER_SWITCH_PROPOSAL)

The A4 plan, its consumer inventory (`VAULT_KEY_CONSUMERS_2026-11-11.json`) and the switch proposal cover only the **Fernet credential store** (`backend/vault_master.key`, `backend/.env`, `crypto_trader_bot.py`, `Vault_Auto_Scanner.py`). A text search found zero references in those three documents to `cryptographic_vault`, `AIBS_AES`, `vault_router` or `vault_keys`. Two further secret-bearing surfaces exist and need their own lanes under the same preservation rules:

| Lane | Surface | Relationship to A4 |
| --- | --- | --- |
| A4-F (existing) | Fernet store: `vault_master.key` + `.env` values | Unchanged. Existing plan, private preservation receipt and source160 admission continue. `vault_master.key` is tracked in the current index and present in `origin/main`; treat it as exposed (plan step 8 already separates history remediation). |
| A4-P (new) | AES-GCM payload layer: `cryptographic_vault.py`, three decrypt sites, five browser helpers | No at-rest ciphertext has been identified; the only established producer is the inbound HTTP envelope, and H2 means legacy envelopes carry their own plaintext. This lane is mainly a code fix plus retirement, not a data re-encryption. |
| A4-K (new) | Plaintext credential table `vault_keys` seeded by `vault_router.py` | Not encrypted by either mechanism. Requires credential revocation (owner), seed removal in source, and a reviewed row cleanup. |

Do not use the Fernet key as an input to A4-P or A4-K, and do not route A4-K rows through the Fernet scanner.

## 4. Proposed fix and migration — approval required per step

### Phase 0 — owner actions (no code dependency)

1. Revoke and replace the four C1 credentials in their provider accounts; review provider activity logs.
2. Confirm repository visibility decisions for `origin` (outstanding in the handoff).
3. Keep the A4-F exposure disposition for `vault_master.key` as already planned.

### Phase 1 — backend source fix (one focused patch; no live restart implied)

| File | Change |
| --- | --- |
| `backend/modules/vault_router.py` | Remove the four literal entries; read optional values from environment only, as for PayPal/Stripe. Move `init_vault_db()` from module scope to explicit startup so import has no database side effect. |
| `backend/core/cryptographic_vault.py` | Remove default passphrase/salt; fail closed (vault unavailable) when either variable is absent. Introduce envelope v2 `{v, kid, iv, ct}` with associated data binding route and authenticated principal. Accept v1 legacy only behind an explicit opt-in flag defaulting to off after the transition window, never when a caller supplies a key. Remove module aliases `aesgcm`, `AES_SECRET_KEY` and `get_active_key`. |
| `backend/AI_BS_Backend.py` | Remove `rawFallback` substitution at both sites; failed decryption returns 400. Remove `/api/security/decrypt`, or add `/api/security` to the admin boundary if a retained caller is identified. Return a generic error message. Stop importing the removed aliases. |
| `backend/test_aes_e2e_encryption.py` | Expect 401/403 without credentials; reject `rawFallback`; legacy refused when flag off; fail-closed startup; v2 round trip and tamper rejection. |

Verification: 10–15-check smoke profile on synthetic data only; full regression reserved for the pre-apply gate.

### Phase 2 — browser helpers

Edit `frontend/src/components/security.js` (sync source of truth) to remove `DEFAULT_AES_*` and `LEGACY_RAW_KEY`; let `frontend/scripts/sync_mirrors.py` propagate to the other copies, run from the intended checkout only. No client receives an at-rest key; clients rely on authenticated TLS. `vault_old/` remains an unbuilt archive. Rebuild and hosting follow their own authorization.

### Phase 3 — data handling (isolated copy first)

1. **Inventory (counts only):** rows in `vault_keys` and `vault_data` for the database selected by `vault_router.py:17–22`; whether any request log, proxy capture, queue or export retains chat request bodies.
2. **Preserve:** SQLite backup-API copies of the affected database with hashes, held under the private preservation rules, before any change.
3. **A4-K rows:** after Phase 0 revocation, delete or replace the four `system-*` seeded rows on an isolated copy; reconcile counts; then repeat on the live file in a reviewed window. Decide separately whether remaining `apiKey` values need at-rest encryption; if so, use a server-only v2 key with key ID, resumable batches, per-row decrypt-back verification and rollback.
4. **A4-P retained envelopes:** if the inventory finds retained legacy requests, treat them as plaintext-bearing records under retention policy (H2), not as ciphertext needing re-encryption. If none are found, record that result.
5. **Retirement:** after all supported clients move and verification passes, remove the legacy flag, old bundles and cached assets. Public history and old clients may retain the old material indefinitely.

### Acceptance

- No credential literals in tracked source; the four C1 credentials revoked (owner receipt).
- Vault refuses to start without configuration; no built-in default key path.
- Unauthenticated decrypt returns 401/403 or the route is absent; `rawFallback` rejected.
- v2 round trip, tamper and legacy-flag tests pass on synthetic data.
- Database row counts reconcile before/after; backup restore passes integrity check.
- Separate receipts for credential revocation, source fix, data cleanup and repository/history remediation, consistent with A4 plan step 9.

## 5. Not done here

No code edits, test runs, database reads, environment reads, provider contact, gateway inspection, history rewrite or visibility change. Gateway protection of `/api/security/decrypt` and actual row counts remain UNVERIFIED. This draft does not modify the A4 architecture documents; folding these lanes into them is a separate owner-approved edit.
