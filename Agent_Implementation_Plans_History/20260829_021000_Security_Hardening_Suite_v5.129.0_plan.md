# Implementation Plan: 5-Tier End-to-End Security Hardening Suite (v5.129.0)

Implement an end-to-end security architecture hardening across all 5 tiers of the AI-BS ecosystem, ensuring 100% local, zero-cost, open-source compliance.

---

## User Review Required

> [!IMPORTANT]
> **Zero Disruption to Local Development**: Localhost and 127.0.0.1 daemons (Ollama, ComfyUI, OBS signaling, Vite dev server) are automatically whitelisted from rate limiting and retain instant access to avoid breaking internal workflows.

---

## Proposed Changes

### Phase 1: Tier 1 & 2 — Ingress Security Headers, Explicit CORS & In-Memory Rate Limiting

#### [NEW] [backend/security/rate_limiter.py](file:///C:/AI-BS/backend/security/rate_limiter.py)
- Sliding-window in-memory IP rate limiter:
  - 120 req/min for general GET endpoints.
  - 20 req/min for broadcast, CMS, and admin POST routes.
  - Returns `429 Too Many Requests` with `Retry-After` header.
  - Whitelists local loopback `127.0.0.1` and `localhost`.

#### [MODIFY] [backend/AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Replace wildcard CORS `allow_origins=["*"]` with explicit domain array and regex pattern (`ai-bs-dashboard.web.app`, `stehouwer-publishing.com`, `localhost:*`, `127.0.0.1:*`).
- Inject `SecurityHeadersMiddleware` adding OWASP protection headers (`nosniff`, `SAMEORIGIN`, `strict-origin-when-cross-origin`, `Permissions-Policy`, `HSTS`).

---

### Phase 2: Tier 3 — Automated SQLite Backup & Integrity Verification Engine

#### [NEW] [backend/scripts/backup_databases.py](file:///C:/AI-BS/backend/scripts/backup_databases.py)
- Performs online `sqlite3.backup()` across all `.sqlite` databases in `saved_data/` to `E:\AI_BS_Resources\Backups\YYYYMMDD_HHMMSS\`.
- Computes SHA-256 integrity hashes for all backup files and writes `checksums.sha256`.
- Enforces 7-day rolling snapshot retention policy.

#### [NEW] [backend/routers/security_router.py](file:///C:/AI-BS/backend/routers/security_router.py)
- `GET /api/security/health`: Returns overall security status, active middlewares, and rate limit stats.
- `GET /api/security/backups`: Returns snapshot history and checksum validation reports.
- `POST /api/security/backups/run`: Triggers on-demand database backup.

---

### Phase 3: Tier 4 — Cryptographic Admin Bearer Token (`X-Admin-Key`) Protection

#### [NEW] [backend/security/auth_guard.py](file:///C:/AI-BS/backend/security/auth_guard.py)
- `verify_admin_key`: FastAPI dependency verifying `X-Admin-Key` header against `.env` / `AI_BS_ADMIN_KEY`.
- Protects destructive administrative routes (`/api/admin/*`, `/api/compute/toggle_mode`, `/api/daemons/start`, `/api/daemons/stop`, `/api/security/backups/run`).

---

### Phase 4: Tier 5 — Local Anti-Tamper File Integrity Watchdog

#### [NEW] [backend/aibs_security_watchdog.py](file:///C:/AI-BS/backend/aibs_security_watchdog.py)
- Computes baseline SHA-256 checksums of critical files (`AI_BS_Backend.py`, `Launch_AI_BS.bat`, `.env`, `backend/modules/`).
- Runs background verification loop every 60 seconds.
- Logs tamper alerts to `saved_data/security_alerts.json` and updates `SystemHealthTab`.

---

### Phase 5: Verification, Live Deployment & Master Ledgers Sync (v5.129.0)

#### [MODIFY] UI Version Badges
- Update version badges to `v5.129.0` across:
  - `frontend/App.jsx`
  - `frontend/components/Sidebar.jsx`
  - `frontend/components/TopNavbar.jsx`
  - `frontend/components/ChatTab.jsx`
  - `frontend/src/components/EcosystemBlueprintTab.jsx`
  - `frontend/src/components/BroadcastStudio.jsx`

#### [EXECUTE] Build & Deployment
- Run `npm run build` and `firebase deploy --only hosting --non-interactive` in `C:\AI-BS\frontend`.

#### [MODIFY] Master Ledgers & Ecosystem Manual
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` (`v5.129.0`).
- Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (`v5.129.0`), persist versioned copy to `saved_data/artifacts/20260829_AI_BS_Master_Ecosystem_Manual.md`, and log in `NotebookLM_Records/artifact_history.md`.
- Append entries to `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.

---

## Verification Plan

### Automated Verification
- Run standalone test script `backend/test_security_suite.py` validating:
  1. Security headers returned on HTTP responses.
  2. Rate limiting triggering `429` on excessive rapid requests.
  3. `backup_databases.py` successfully backing up databases to `E:\AI_BS_Resources\Backups` with valid SHA-256 checksums.
  4. `X-Admin-Key` verification blocking unauthorized admin requests.
  5. Anti-tamper file watchdog correctly hashing monitored files.

### Deployment Verification
- Verify successful Firebase deploy to `https://ai-bs-dashboard.web.app`.
