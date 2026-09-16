# Implementation Plan: Omni Operations & Live Audit Hub (`OperationsAuditHubTab.jsx`)

Architectural specification and rollout plan for a centralized, real-time super-hub in AI-BS displaying live user tasks, continuous autosaves, media generation queues (ComfyUI photo/video), multi-admin database submissions, and system-wide error/crash diagnostics.

> [!IMPORTANT]
> **Strict Zero-Mock Mandate**: Every card, table, chart, status indicator, and feed in this Hub connects directly to live operating system processes (`psutil`), actual SQLite database tables, the active ComfyUI REST/WebSocket API (`http://127.0.0.1:8189`), and raw `.log` files in `C:\AI-BS\logs\`. No synthetic or simulated data is permitted.

---

## User Review Required

> [!NOTE]
> In compliance with the **Interactive Side-Box & Suggestion Commenting Protocol** and the **Strict Prohibition of Auto-Proceed**, this plan is staged for your line-by-line review. Execution will remain halted until you provide explicit manual confirmation in the chat.

1. **Navigation Placement**:
   - **Option A (Recommended)**: Mount inside **Stehouwer Publishing** (Admin HQ) as a primary operational tab alongside Command Center and System Health.
   - **Option B**: Mount as a standalone 6th Master Hub in `Sidebar.jsx` named **Omni Operations & Live Audit Hub** (`audit_hub`).
2. **Process Management Controls**:
   - Allow admins to issue graceful restart (`SIGTERM` / supervisor restart) or hard kill (`SIGKILL`) directly from the Active Tasks panel for hung daemon processes.
3. **Log Parser Scope**:
   - Automatically ingest and categorize errors from all 30+ daemons in `C:\AI-BS\logs\`, with direct in-browser log streaming and tailing.

---

## Technical Architecture & Component Design

```
                     ┌─────────────────────────────────────────────────────────────┐
                     │            AI-BS Dashboard Frontend (Vite / React)          │
                     │                 OperationsAuditHubTab.jsx                   │
                     └──────────────────────────────┬──────────────────────────────┘
                                                    │ Live Polling / SSE / REST
                                                    ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │          FastAPI Master Cognitive Backend (Port 8080)       │
                     │          backend/routers/operations_audit_router.py         │
                     └──────┬──────────────┬──────────────┬──────────────┬─────────┘
                            │              │              │              │
     ┌──────────────────────▼┐  ┌──────────▼────────┐  ┌──▼───────────┐  │
     │ Live System Engine    │  │ ComfyUI Bridge    │  │ SQLite Multi-│  │
     │ - psutil Process Scan │  │ - Port 8189 Queue │  │   Tenant DBs │  │
     │ - Active TCP Ports    │  │ - Prompt History  │  │ - state.db   │  │
     │ - RAM & CPU Telemetry │  │ - Output Media    │  │ - vault.db   │  │
     └───────────────────────┘  └───────────────────┘  │ - crm/leads  │  │
                                                       └──────────────┘  │
                                ┌────────────────────────────────────────▼────────┐
                                │ Daemon Error Engine & Crash Diagnostics         │
                                │ - Scans 30+ *.log files in C:\AI-BS\logs        │
                                │ - Extracts [ERROR], [CRITICAL], Tracebacks      │
                                │ - Identifies Hung Sockets & Stopped Tasks       │
                                └─────────────────────────────────────────────────┘
```

---

## Proposed Changes

### Backend Engine

#### [NEW] [operations_audit_router.py](file:///C:/AI-BS/backend/routers/operations_audit_router.py)
A high-throughput, real-time diagnostic router exposing 6 specialized endpoints:
1. `GET /api/operations/processes`:
   - Inspects all running system processes via `psutil`.
   - Filters AI-BS specific processes (Python daemons, Vite, Go engine, Ollama, ComfyUI, Cloudflared, PeakMiner, Oyster).
   - Returns PID, process name, RSS memory (MB), CPU usage (%), command-line arguments, start time, and active listening ports.
2. `POST /api/operations/process-control`:
   - Allows authorized admins to terminate (`kill`) or trigger supervised restarts for stalled processes.
3. `GET /api/operations/media-workloads`:
   - Real-time query to ComfyUI (`http://127.0.0.1:8189/queue` and `http://127.0.0.1:8189/history`).
   - Direct file audit of generated outputs in `C:\AI-BS\ComfyUI\output` and `E:\ComfyUI_windows_portable\ComfyUI\output`.
   - WSL2 Nginx RTMP (`1935`) and HLS (`8089`) streaming broadcast ingestion health.
   - Wave Studio audio stems and recording session status in `C:\AI-BS\saved_data`.
4. `GET /api/operations/saves-and-work`:
   - Live continuous autosave log from `C:\AI-BS\backend\state.db` and `session_history_archive.json`.
   - File modification auditor tracking files changed in `C:\AI-BS\` within the last 24 hours.
   - Master Architectural Ledger snapshot tracking system version lineage.
5. `GET /api/operations/admin-submissions`:
   - Cross-database live aggregator querying records submitted by admins across:
     - `state.db`: Client profiles, growth leads, scheduled posts, campaign subscribers.
     - `stehouwer_vault.db`: Vault keys, tenant user credits, leads tracker, media vault items.
     - `stehouwer_accounting.db`: Accounting entries, P&L ledgers.
     - `clients.db` & `leads_store.db`: Joey enriched leads, CRM clients, competitors, fleet.
     - `prestige_powerwash.db`: Power washing clients, job work orders, fleet logs.
     - `west_michigan.db`: Property records and marketing history.
   - Categorized by submitter (`client_id` / user identity) and timestamp.
6. `GET /api/operations/error-diagnostics`:
   - Automated parser scanning the tail (200 lines) of all 30+ log files in `C:\AI-BS\logs\`.
   - Regex extraction of `[ERROR]`, `[CRITICAL]`, Python `Traceback`, `ModuleNotFoundError`, `SyntaxError`, `IndentationError`, and socket timeout failures.
   - Calculation of daemon "hang time" and stopped status based on log file last-modified timestamps vs current time.
7. `GET /api/operations/log-tail?logfile=<name>&lines=100`:
   - Streams the raw tail of any selected daemon log file for immediate forensic debugging.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Import and register `operations_audit_router` under `/api/operations`.

---

### Frontend Dashboard Application

#### [NEW] [OperationsAuditHubTab.jsx](file:///C:/AI-BS/frontend/components/OperationsAuditHubTab.jsx)
A responsive, high-contrast dark-mode cybernetic dashboard featuring 5 tabbed sub-views:
1. **Active Tasks & Daemons**:
   - Live status cards for core subsystems (Ollama LLM, ComfyUI, FastAPI, Go Gateway, PeakMiner PoW, ChromaDB, Cloudflare Tunnel).
   - Real-time searchable process table with PID, Memory (MB), CPU (%), Port, Command, and Kill action button.
   - Hardware load metrics (System RAM utilization, CPU load).
2. **Media Generation Pipeline**:
   - Real-time ComfyUI Queue Monitor (Running Prompts vs Pending Queue).
   - Live media output feed with interactive thumbnail preview, video playback, dimensions, file size, and timestamp.
   - Broadcast Ingestion status (RTMP 1935, HLS 8089, OBS 4455).
3. **Work & Autosaves Log**:
   - Chronological audit ledger of all system autosaves, episodic memory consolidations, and artifact updates.
   - Filterable by type (State DB, Memory Ingest, Screenplay Autosave, Architectural Ledger).
4. **Admin User Data Vault**:
   - Unified multi-tenant data browser displaying submissions across all 7 SQLite business databases.
   - Table selector (`crm_leads`, `clients`, `accounting_entries`, `vault_data`, `powerwash_jobs`).
   - Displays real IDs, client tags, timestamps, and payload previews.
5. **System Error & Crash Diagnostics**:
   - Real-time diagnostic alert feed showing active daemon errors, missing modules (e.g. `watchdog`, `httpx`), and failed jobs.
   - Daemon health grid indicating active vs stalled/hung daemons (based on heartbeat timestamps).
   - Embedded interactive log tail viewer with auto-scroll and line search.

#### [MODIFY] [navigationConfig.js](file:///C:/AI-BS/frontend/components/navigationConfig.js)
- Register `operations_audit` tab under `stehouwer_publishing` (or as dedicated hub per user preference).

#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Add lazy import for `OperationsAuditHubTab.jsx` and wire into the main tab render switch statement.

---

## Verification Plan

### Automated Tests
1. Query `GET http://127.0.0.1:8080/api/operations/processes` and verify response contains real PIDs and valid memory footprints.
2. Query `GET http://127.0.0.1:8080/api/operations/media-workloads` and verify ComfyUI queue connectivity and media output array.
3. Query `GET http://127.0.0.1:8080/api/operations/admin-submissions` and verify record counts match SQLite table totals.
4. Query `GET http://127.0.0.1:8080/api/operations/error-diagnostics` and verify error lines from `auto_healer_daemon.log`, `crypto_trader_bot.log`, etc. are correctly extracted.

### Production Build & Deployment Verification
1. Run `npm run build` in `C:\AI-BS\frontend` to confirm bundle compiles cleanly with modular code-splitting.
2. Deploy to Firebase Hosting: `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"`.
3. Synchronize build artifacts to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
4. Inspect live web app at `https://ai-bs-dashboard.web.app` to verify real-time streaming and responsive rendering.
