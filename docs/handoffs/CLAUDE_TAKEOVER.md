# Claude Takeover: AI-BS

Written 2026-11-21 by Claude (cloud session) for the local Claude Code session in `C:\AI-BS`.
Owner: Brett Stehouwer. Untracked file; do not commit without owner approval.

Read this whole file before doing anything. It replaces the need to see the earlier conversation.

---

## 1. Operating rules (owner's current instructions; these override AGENTS.md)

1. **Start every reply with "This is Claude."**
2. **Nothing changes without explicit owner approval:** no commits, pushes, branch or worktree creation, stashes, discards, deletions, `.gitignore` edits, migrations, service restarts, or `git fetch`/`pull`/`push`. Read-only investigation is always allowed.
3. **AGENTS.md "Pre-Approved Execution" (L28 at `64fad28`) and "unrestricted write authority" (L103) do NOT apply.** AGENTS.md L151 says current instructions govern; these are the current instructions. Do not install or follow the repo skill `.agents/skills/autonomous-execution`.
4. **Never print, quote, or summarize a secret value** (keys, passphrases, salts, tokens, order IDs). Report path, line, and category only. Do not open `.env` files, `.aibs-private`, vaults, key files, or browser profiles.
5. **Do not touch live services or ports:** 8000 (Go engine), 8002 (Chroma), 8007 (structural dip engine), 8017 (mobile crypto relay), 8025/8026 (dispatch/Valhalla, bound to 0.0.0.0), 8080 (backend), 5173 (Vite), 11434 (Ollama). No live trading credentials.
6. **Do not run `frontend/scripts/sync_mirrors.py`.** It falls back to the hardcoded `C:/AI-BS/frontend` and can rewrite the main checkout's mirrors from inside a worktree.
7. **Do not import backend code to "test" it.** Importing the calendar router opens `C:\AI-BS\database\calendar.db` (hardcoded absolute path); the vault initializes cipher state at import; the backend runs a schema migration at module scope.
8. Owner prefers **severity-tiered findings with file:line references**. Label facts "verified now (command/file:line)" vs "from older notes" vs "observed during inventory, capture date unverified".
9. For high-stakes steps (vault migration, history purge, credential handling), get an independent review pass that has not seen the work.

---

## 2. Repository state

- Main checkout: `C:\AI-BS`, branch `codex/audit-v532976-20261031`, HEAD `64fad2871e0a716d9964f506bdef1050612b173d`.
- **137 tracked files modified, uncommitted** (+10,934 / −2,014). ~6,966 untracked entries (`-unormal` grouping, observed 2026-11-21T17:23:33Z).
- **`64fad28` does not boot or build on its own.** Its backend imports modules never committed; its build calls `sync_mirrors.py`, never committed. The running system depends on files that exist only on disk.
- Remotes:
  - `origin` → `github.com/brettstehouwer-collab/AI-BS-Core` — **PUBLIC** (verified anonymously 2026-11-21).
  - `stehouwer` → `github.com/brettstehouwer-collab/AI-BS` — not anonymously visible (private or missing; owner to confirm).
- Frontend mirrors: `frontend/src/components/` is the **source of truth**; `sync_mirrors.py` copies it over `frontend/components/`, `frontend/src/components/components/`, `frontend/components/components/` before every `npm run build`. Always edit all four copies identically or the primary only. The app *loads* `frontend/components/ChatTab.jsx` (index.html → main.jsx → App.jsx → SplitPaneIDEWorkspace.jsx → ChatTab).
- Files are CRLF on disk, LF in Git blobs. Compare hashes only within one form.

---

## 3. SECURITY INCIDENT (top priority)

Public `origin` (cached refs; may be stale; older commits not scanned) contains:
- `origin/main` (`e45f1b50`, 2026-10-28): `backend/vault_master.key`, `backend/stehouwer_code_signing.pfx`, credential literals in Hostinger, Resend, and TextBee scripts, Google-key-format literals in two backend scripts, `backend/routers/trading_router.py`.
- `origin/master` (`b99542e8`, 2026-06-29): `AI-BS/backend/key.pem`, `AI-BS/backend/cert.pem`.
- The public frontend contains the vault's default passphrase, salt, and legacy key.
Details by file and line: `docs/drafts/ORIGIN_EXPOSURE_Codex.md`.

**Owner actions (owner does these, not Claude):**
1. Make `AI-BS-Core` private.
2. Rotate, in order: Hostinger, Resend, code-signing certificate (revoke with CA), TextBee, Google API keys (restrict Firebase client keys), TLS key/cert if deployed.
3. Re-encrypt data under `vault_master.key` before retiring it.
4. Check provider logs since 2026-06-29.

**Claude actions after rotation (each needs approval):** credential checklist (one row per credential, no values); history purge with `git filter-repo` + force push; enable GitHub secret scanning and push protection on both repos.

---

## 4. Vault defect (`backend/core/cryptographic_vault.py`)

- L19 `LEGACY_AES_SECRET_KEY = bytes(range(1,33))` — trivially guessable fixed key.
- L22 `DEFAULT_MASTER_PASSPHRASE`, L23 `DEFAULT_SALT` — literals used when env is unset (L65–70).
- L121–124 decryption falls back to the legacy key → legacy-key data is effectively plaintext and forgeable.
- Owner checked: `AIBS_AES_MASTER_PASSPHRASE` and `AIBS_AES_SALT` are **not set** at process, user, or machine level → vault almost certainly runs on the defaults. A launcher could still set them (unverified).
- Commit `37689681` contains the file; it is not reachable from cached `origin` refs. But the same defaults are in the public frontend → **treat all vault ciphertext as readable by anyone who obtains it.**
- **Design problem:** the browser holds the key, so it cannot be secret. Fix = server-only key from env, no defaults, no legacy fallback, TLS + auth for transport.
- **Do NOT set the env var yet.** The vault never tries the default passphrase as a fallback; switching keys now makes existing data unreadable. Migration first.
- **Next step (read-only):** vault trace — runtime config that sets the vars; every backend importer and where its ciphertext lives; every frontend file (sources, four mirrors, built bundles, Firebase-deployed files) holding or deriving the key; legacy-key data; migration proposal ordered so no data becomes unreadable. Codex was given this; result may exist at `docs/drafts/VAULT_TRACE_Codex.md`.

---

## 5. Redactions done (working copy only, never committed)

`docs/agent_sync/current_long_term_goal.json` (tracked, modified):
- L12 `api_key_public_suffix` → `REDACTED-see-credential-store` (was a Crypto.com API key ID).
- L17–19 `bootstrap_sell_fill`, `initial_scalp_buy_fill`, `active_resting_sell_order` → `REDACTED-live-order-record`.
Line count and all 2,025 CRLF endings preserved. L10 `credential_registry_bound` (61 chars) unreviewed.

---

## 6. Integration plan (owner-approved direction; no commits approved)

**Decision:** make the base complete with reviewed baseline commits first, then 15 feature commits.

**Trading code goes to NEITHER remote.** Keep it in a **separate local repository with no remote** (not merely a local branch). Layering: pushable public-safe layer = baseline + feature commits except trading; local-only trading layer on top. The 25 trading files = 23 under `*crypto*` + 2 `*_contract.py` under `*Contract*`.

**`cryptographic_vault.py` = core infrastructure** (owner decision), but **failed review**; it must be fixed (Section 4) before going in any pushable commit.

**Held, never committed:** 4 `scripts/tests/__pycache__/*.pyc`, `backend/matrix_health_report.json`, `docs/viewport_telemetry/probe_run/viewport.json`. Leave contents and index state alone. Ledger: 131 candidates + 6 held = 137.

**`.gitignore` L328–365 privacy rules** (`*accounting*`, `*crypto*`, `*ledger*`, `*NDA*`, `*Contract*`, `*Screenplay*`, `*Film*`, `*Book*`) are intentional (financial records, confidential publishing material) — keep them. They ignore 52 source/CSS files because Windows Git matches case-insensitively (`*NDA*` hits "caleNDAr", "boUNDAry"). Fix = narrow exceptions for code paths, owner-approved, after secret scan. Do not edit without approval.

**Baselines:**
- **B01 frontend (17 paths):** sync helper, four JS helpers, three primary stylesheets + nine mirrors. Static imports resolve; build unverified; version-file byte check may trip on CRLF.
- **B02 backend (55 files):** covers every *unconditional* import from `AI_BS_Backend.py`. Acceptance = static trace only until DB isolation exists. Known defects (not blockers): no provider for `routers.bioinformatics_router`, `imagegen_agent`, `local_imagegen`, `.media_chromadb_vault`; three import sites request missing symbols (daemon crash recovery, syndication audit, heuristics fallback).
- `public_market_data.go` and the audit watcher depend on feature-commit changes; do not add them early.

**Feature commit order (Codex-corrected):** 1 docs · 2 sensitive docs (after review) · 3 release/version markers (package.json version only) · 4 audit store contract · 5 local inference + `personal_memory_scope.py` · 6 builder unavailable/503 (incl. 503 hunk of AI_BS_Backend.py) · 7 screenwriting · 8 audio/film (incl. chat-films registration hunk) · 9 chat streaming/coding mode (incl. SSE/correlation hunks of hybrid_reasoning_engine) · 10 ports/routing (incl. port edits in crypto-named panels) · 11 trading (LOCAL-ONLY repo) · 12 identity/analytics · 13 backend entry payments/ledger · 14 native studio · 15 hosting + new build commands.
Full ledger with hunk assignments: `docs/drafts/PHASE2_Codex.md`.

**Secret scans:** tracked diff + 178 baseline + B02 files scanned; only real findings were the goal-JSON items (now redacted) and the vault defaults. `BrandCampaignManager.jsx` hits are false positives (runtime input). `validate_syndication_matrix.py:269` IndexNow key is public by design.

---

## 7. Completed side task: `/status` "Checked at"

Branch `ui/status-checked-at` at `d64b0d966c75b2fe39348d900601eb150fd6d9ce` (parent `afb313a`), worktree `C:\AI-BS\t\worktrees\ui_status_checked_at`. Reviewed by two tools. **Integration deferred** until owner names a target and base SHA; then rerun four fixtures, verify four-copy SHA-256 parity, render a fixture-backed reply in the target UI (intercept `/api/executive/daemons`, dev port ≠ 5173). Handoff: `docs/handoffs/status-checked-at.md` in that worktree.

---

## 8. Reference reports (`C:\AI-BS\docs\drafts\`)

`PROJECT_MAP.md` (accepted) · `TRIAGE_Codex.md` · `TRIAGE_antigravity.md` · `PHASE2_Codex.md` · `PHASE2_SECRETS_antigravity.md` · `BASELINE_B1_Codex.md` · `BASELINE_B1_SECRETS_antigravity.md` · `BASELINE_B1_IGNORES_antigravity.md` (note: its 53-vs-52 discrepancy is a CRLF parsing artifact; true count 52) · `BASELINE_B2_Codex.md` · `BASELINE_B2_SECRETS_antigravity.md` (understated the vault; see Section 4) · `ORIGIN_EXPOSURE_Codex.md` · `VAULT_TRACE_Codex.md` (if present).

Other facts: ChromaDB primary 8001 (no listener observed), secondary 8002 (observed). `/health` = Matrix Doctor (`POST /api/tools/execute`); `/status` = `GET /api/executive/daemons` (Unix-seconds timestamp, `daemon_manager.py:421`); `/backend status` = browser-localStorage check (`aibs.local-maintenance.pending.v1`), then `GET /api/health`.

---

## 9. What to do first

1. Confirm with the owner: is `AI-BS-Core` private yet, and which credentials are rotated?
2. If `docs/drafts/VAULT_TRACE_Codex.md` exists, verify it against the files; otherwise run the vault trace yourself (read-only, Section 4).
3. Draft the vault fix + data migration as its own task for owner approval.
4. Then resume the baseline: present B01 as a concrete commit proposal for approval.
