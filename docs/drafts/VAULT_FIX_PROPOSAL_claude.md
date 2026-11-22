# Vault Fix Proposal (Claude) — DRAFT, approval required

2026-11-21. Verifies `docs/drafts/VAULT_TRACE_Codex.md` against code and proposes the fix.
Nothing in this file has been executed. No secret values appear here.

## A. Verification of Codex's trace

| Claim | Result | Evidence |
|---|---|---|
| `backend/.env` is loaded before the AES vault initializes | **CONFIRMED** | `AI_BS_Backend.py:222` imports `modules.vault_router`; `vault_router.py:124` runs `init_vault_db()` at module scope, which calls `load_dotenv(backend/.env)` at L62–65. The vault import is later, at `AI_BS_Backend.py:3309`. |
| `backend/.env` contains both variable names | ACCEPTED (name search only; file not opened per rules) | Codex Appendix A. Whether the assignments are non-empty is **unverified** — owner check below. |
| Ciphertext is transport-only (inbound HTTP), not stored | ACCEPTED, consistent with code read | Decrypt sites: `/api/security/decrypt` (L3571), `/api/chat` + `/v1/chat/completions` (~L9027–9060), catch-all `/{full_path:path}` (~L14427–14459). No persistence call at those sites. |
| Five frontend `security.js` copies hold the defaults and legacy key; on public `origin/main` | ACCEPTED (spot-checked `frontend/src/components/security.js` present locally) | Codex §3–4. Not in `frontend/dist`, so not in the current Firebase deploy per local files; live site unverified. |

**Correction to my earlier statement:** I said the vault "almost certainly" runs on its built-in defaults. That was wrong. The backend loads `backend/.env` first, so if those assignments are non-empty it runs on a configured passphrase and salt. The Windows environment check could not see that.

## B. New finding

**HIGH — `/api/security/decrypt` is an unauthenticated decryption service** (`backend/AI_BS_Backend.py:3571–3589`).
- It decrypts any submitted IV + ciphertext with the active key, falls back to the legacy key, and returns the plaintext.
- It is **not** in `AdminExecutionBoundaryMiddleware.SENSITIVE_PREFIXES` (L1822–1843; `/api/security/backups` is, `/api/security/decrypt` is not) and not in `security/vault_access.PREFIXES`. No handler-level auth dependency.
- Effect: anyone who can reach the backend can decrypt any captured envelope, even if `backend/.env` holds a strong secret passphrase. Reachability beyond localhost depends on the Cloudflare tunnel's routes (unverified).
- `/api/chat` and `/v1/chat/completions` ARE admin-protected (they are in SENSITIVE_PREFIXES). The catch-all route decrypts envelopes for paths outside the list — needs the same check.

## C. Proposed fix (each phase = one reviewed commit, owner approval per phase)

Because ciphertext is transient, this is a **removal of a flawed transport layer**, not a data migration. No stored data becomes unreadable.

**Phase 0 — close the oracle (small, do first).**
Add `/api/security/decrypt` to `SENSITIVE_PREFIXES`, or delete the route if nothing legitimate calls it (Codex found only tests). Make the catch-all refuse encrypted envelopes from non-admin callers. Test: unauthenticated POST returns 403; tests updated.

**Phase 1 — confirm nothing is stored (read-only, owner input).**
Owner confirms whether any proxy, tunnel log, queue, or backup records raw request bodies. If none: no ciphertext exists to migrate. If some: back those up before Phase 3.

**Phase 2 — stop using payload encryption.**
Clients send plain JSON over HTTPS (the tunnel already terminates TLS). Backend keeps accepting envelopes only from authenticated callers during a short overlap, logging (counts only) any envelope still received, to find remaining senders.

**Phase 3 — remove the keys from code.**
Delete `DEFAULT_MASTER_PASSPHRASE`, `DEFAULT_SALT`, `LEGACY_AES_SECRET_KEY`, and the legacy fallback (`cryptographic_vault.py` L19, L22–23, L121–124). Make the vault **fail closed** if the env variables are missing. Delete the five `security.js` copies and `frontend/vault_old/App_v1.4.1.jsx` (or remove their key material). Rebuild and redeploy the frontend.

**Phase 4 — rotate.**
Replace the `backend/.env` AES passphrase and salt (they may match the public defaults; unverified). After Phase 2–3 nothing depends on them, so rotation breaks nothing.

**Out of scope, do not touch:** the separate Fernet store (`backend/Vault_Auto_Scanner.py:218–259`, read by `crypto_trader_bot.py`) and `vault_router`'s `vault_keys` table. Those are a different system and need their own review.

## D. Owner checks needed (print True/False only, never values)

```powershell
Select-String -Path C:\AI-BS\backend\.env -Pattern '^\s*AIBS_AES_MASTER_PASSPHRASE\s*=\s*\S' -Quiet
Select-String -Path C:\AI-BS\backend\.env -Pattern '^\s*AIBS_AES_SALT\s*=\s*\S' -Quiet
```
True = a non-empty assignment exists (backend uses it). False = defaults are in effect.

Also: does the Cloudflare tunnel `ai-bs` route public traffic to backend port 8080? (Determines whether Phase 0 is an emergency.)
