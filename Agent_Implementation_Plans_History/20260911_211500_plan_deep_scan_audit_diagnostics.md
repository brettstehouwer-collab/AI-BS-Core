# Comprehensive Deep-Scan Audit Diagnostics: Frontend-to-Backend Connectivity & System Integrity

Execute a systematic, multi-domain forensic audit of the entire AI-BS frontend codebase (`frontend/`), cross-referencing all network calls, API routes, WebSockets, media references, and telemetry streams against the FastAPI backend (`backend/AI_BS_Backend.py`, `backend/routers/*.py`) and associated ecosystem daemons.

## User Review Required

> [!IMPORTANT]
> The audit is structured into 4 sequential diagnostic phases:
> 1. **Vite Production Compilation & Static Import Verification**: Testing the entire frontend bundle for missing imports, syntax errors, and broken dependencies.
> 2. **Automated Route & Communication Extraction**: Parsing every frontend component (`.jsx`, `.js`, `.tsx`, `.ts`) for `fetch`, `axios`, `WebSocket`, `EventSource`, `getApiBase()`, and relative URLs.
> 3. **Backend Route Cross-Referencing & Discrepancy Matrix**: Comparing all frontend target endpoints against registered FastAPI and daemon routes to pinpoint 404 dead-ends, HTTP method mismatches, or missing route handlers.
> 4. **Architectural Guardrail Checks**: Validating `X-Client-ID` multi-tenant header isolation, dynamic media routing (`BACKEND_URL`), and Zero-Mock real money integrity in financial tabs.

> [!WARNING]
> Any identified runtime crashes, missing backend endpoints, or media routing violations will be cataloged with file paths, line numbers, and actionable remediation patches.

## Open Questions

None at this time. Standard production port allocations (8080 FastAPI, 8000 Go, 8010 SHM, 8189 ComfyUI, 11434 Ollama) and Cloudflare Tunnel (`https://api.brettstehouwer.live`) will serve as baseline targets.

---

## Proposed Changes

### Diagnostic Engine

#### [NEW] [audit_frontend_backend_connectivity.py](file:///C:/AI-BS/backend/scripts/audit_frontend_backend_connectivity.py)
- AST and regex-based scanner parsing all JSX/JS files in `frontend/src/` and `frontend/components/`.
- Extracts:
  - Exact API paths called (`/api/...`, `/chat/...`, etc.).
  - HTTP verbs used (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`).
  - Base URL schemes (`getApiBase()`, `window.location.origin`, `BACKEND_URL`, hardcoded hostnames).
  - WebSockets (`ws://`, `wss://`, ports 8010, 8888, etc.).
  - Media/Image `src` references (detecting any un-prefixed relative paths violating dynamic media routing).
  - Mock financial data patterns in accounting/crypto tabs.
- Introspects FastAPI application route table by importing `app` from `backend.AI_BS_Backend` and enumerating all routes, methods, and URL parameters.
- Emits a comprehensive discrepancy matrix:
  - **Matched Endpoints**: Confirmed working frontend-to-backend channels.
  - **Missing Backend Endpoints**: Frontend calls hitting non-existent backend routes (definite 404s).
  - **Method Mismatches**: e.g., frontend sending POST where backend only accepts GET.
  - **Media Routing Violations**: Images/media missing dynamic `BACKEND_URL` prefixing.
  - **Tenant Header Gaps**: Calls omitting `X-Client-ID` where backend enforces tenant isolation.

---

### Frontend Diagnostics & Verification

#### [MODIFY] [Vite / Frontend Scripts](file:///C:/AI-BS/frontend/)
- Run `npm run build` using PowerShell to ensure production bundle compiles with 0 errors.
- Verify that `frontend/src/config/api.js` correctly handles Capacitor mobile, local PC (localhost/127.0.0.1:8080), LAN IPs, and Cloudflare Tunnel (`https://api.brettstehouwer.live`).

---

### Ecosystem Ledgers & Documentation

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Log deep-scan audit findings, matched vs missing routes, and remediation actions.

#### [MODIFY] [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Bump version and record diagnostic audit status.

---

## Verification Plan

### Automated Tests
1. **Compilation Check**:
   - `powershell -ExecutionPolicy Bypass -Command "npm run build"` in `C:\AI-BS\frontend`
2. **Connectivity & Route Match Audit**:
   - Run `pyppeteer_env\Scripts\python.exe backend\scripts\audit_frontend_backend_connectivity.py`
3. **Automated Test Suite**:
   - Run Python backend test suite verifying core routers: `pyppeteer_env\Scripts\python.exe -m pytest backend/tests/` (or relevant test files).

### Manual Verification
- Review generated audit diagnostics report and verify that all critical frontend interfaces (ChatTab, ScreenwritingTab, ProcessMemoryLabTab, AeoTracker, BroadcastStudio, etc.) have 100% route coverage in the backend.
