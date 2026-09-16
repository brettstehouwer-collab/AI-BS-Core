# Implementation Plan: System-Wide Error Log Check & Diagnostic Repair

## Objective
Audit and verify the operational integrity of the AI-BS ecosystem across frontend build bundles, backend Python source code, background daemons, log files, and active HTTP endpoints.

## Proposed Changes

### System Audit & Diagnostics
- **Frontend Verification:** Execute `npm run build` using `powershell -ExecutionPolicy Bypass` in `c:\AI-BS\frontend`.
- **Backend Syntax Verification:** Execute `py_compile` across all 4,510 Python files in `c:\AI-BS\backend` and root.
- **Log Stream Analysis:** Parse all `.log` files in `c:\AI-BS\logs\` for tracebacks, syntax errors, and connection faults.

### Code & Configuration Repairs
#### [MODIFY] [drip_trader_daemon.py](file:///c:/AI-BS/Crypto-Swarm/drip_trader_daemon.py)
Purge 9,159 corrupted null bytes (`\x00`) causing `SyntaxError: source code cannot contain null bytes`.

#### [MODIFY] [wallet_tracker_daemon.py](file:///c:/AI-BS/backend/wallet_tracker_daemon.py)
Add fallback path to check project root `.env` (`WORKSPACE_DIR.parent / ".env"`) when `backend/.env` is absent.

#### [MODIFY] [news_firehose_daemon.py](file:///c:/AI-BS/backend/core/news_firehose_daemon.py)
Add standard `User-Agent` HTTP header to RSS feed GET requests to prevent HTTP 403 Forbidden errors.

## Verification Plan
1. `npm run build` -> 6,403 Vite modules transformed, zero build/type errors.
2. `py_compile` -> 0 syntax errors across 4,510 Python files.
3. HTTP endpoint health checks -> Ports 8000, 8001, 8080, 5173, 11434 return HTTP 200 OK.
