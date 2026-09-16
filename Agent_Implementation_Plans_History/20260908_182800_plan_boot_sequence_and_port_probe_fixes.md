# Implementation Plan: AI-BS Matrix Boot Sequence & Subsystem Port Resolution

Comprehensive diagnostic analysis and remediation plan for resolving the port binding warnings and launcher behavior identified in the system startup logs.

## User Review Required

> [!IMPORTANT]
> **No code or configuration changes will be executed until you review this plan and provide explicit manual confirmation in chat.**

> [!NOTE]
> All findings below were verified via live runtime inspections, socket connection probes, process scans, and repository git commit history.

---

## Diagnostic Findings & Root Cause Analysis

### 1. Ports 1935 (RTMP) & 8089 (HLS) — False-Positive Warnings
- **Status:** **Both services are fully ONLINE and healthy.**
- **Diagnostic Proof:** Direct socket probe to `127.0.0.1:1935` and `127.0.0.1:8089` succeeded instantly with `TcpTestSucceeded: True`.
- **Root Cause:** In `C:\Users\footb\.wslconfig`, WSL2 is configured with `networkingMode=mirrored`. When Nginx runs inside WSL2 listening on `0.0.0.0:1935` and `0.0.0.0:8089`, the listening sockets reside in the Linux kernel. Windows host `netstat -an` does not list WSL2 sockets under state `LISTENING`. Because `Launch_AI_BS.bat` relies on `netstat -an | find ":%PORT% " | find "LISTENING"`, the probe fails for 10 seconds and throws a false warning.

### 2. Port 8085 (Ubuntu-Bio Bridge) — Subshell Termination & Mirroring Blindness
- **Status:** Virtual environment exists (`/opt/bio_bridge_env`) and `main.py` runs cleanly.
- **Root Cause:** 
  1. `Launch_AI_BS.bat` invokes `wsl.exe -d Ubuntu -u root -- bash /mnt/c/AI-BS/backend/ubuntu_bio_bridge/start_fastapi.sh`. That script runs `nohup uvicorn ... &` and immediately exits. When the top-level `wsl.exe` invocation exits, WSL terminates background subshells detached from a persistent parent.
  2. Even when running, `netstat LISTENING` fails due to mirrored networking mode as explained above.

### 3. Port 8008 (Supabase Kong Gateway) — Phantom Probe for Retired Container
- **Status:** **Obsolete / Not Part of Active Architecture.**
- **Root Cause:** AI-BS runs on local SQLite databases (`state.db`, `aibs_master.db`, etc.) and local ChromaDB (`8002`). Docker is not installed on the Windows host, and inside WSL, Docker is dedicated exclusively to Clore.ai hosting/revenue containers. There is no command in `Launch_AI_BS.bat` that launches Supabase. The probe `call :WaitForPort 8008 "Supabase Kong Gateway" 5` blocks for 5 seconds and warns every time.

### 4. Port 4455 (OBS Studio WebSocket) — Deprecated Service Probe
- **Status:** **Deprecated / Intentionally Disabled.**
- **Root Cause:** OBS Studio was superseded by the native DirectX 11 NVENC Broadcast Kernel (`aibs_broadcast_kernel.py` on Port 8088). As documented in `backend/aibs_obs_orchestrator.py`:
  > *"AI-BS Native Orchestrator (OBS Eliminated) ... All broadcasting is handled directly by aibs_broadcast_kernel.py. OBS is completely disabled and will never be spawned."*
  Despite OBS being eliminated from active broadcasting, an obsolete probe `call :WaitForPort 4455 "OBS Studio WebSocket" 5` remained in `Launch_AI_BS.bat`.

### 5. Line 20 Batch File Syntax Error (`'Network' is not recognized`)
- **Status:** Benign syntax bug in `Launch_AI_BS.bat`.
- **Root Cause:** Line 20 reads:
  `echo [1.5/9] Verifying Windows Defender Firewall Streaming & Network Access Ports...`
  The bare `&` is interpreted by `cmd.exe` as a command separator, attempting to execute `Network Access Ports...`.

### 6. Electron Sovereign Studio Child Process Collision (`exit code: 1`)
- **Status:** Port collision between launcher background daemons and Electron child spawner.
- **Root Cause:** When `AI-BS Sovereign Studio.exe` launches, its internal `spawnEcosystem()` unconditionally executes `brain_backend.exe` (Port 8080) and `aibs_engine.exe` (Port 8000). Because `Launch_AI_BS.bat` has already started both daemons in the background, the child processes immediately crash with exit code 1 due to `EADDRINUSE`.

---

## Proposed Changes

### [Component 1] Batch Orchestrator: [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)

#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
1. **Escape Ampersand on Line 20:**
   Change `Streaming & Network Access Ports` to `Streaming ^& Network Access Ports`.
2. **Persistent Daemon Spawn for Ubuntu-Bio Bridge:**
   Update line 52 to launch uvicorn directly as the entry command:
   ```bat
   powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'wsl.exe' -ArgumentList '-d Ubuntu -u root -- /opt/bio_bridge_env/bin/python3 -m uvicorn --app-dir /mnt/c/AI-BS/backend/ubuntu_bio_bridge main:app --host 0.0.0.0 --port 8085' -WindowStyle Hidden"
   ```
3. **Remove Phantom / Retired Probes:**
   Remove `call :WaitForPort 8008 "Supabase Kong Gateway" 5` and `call :WaitForPort 4455 "OBS Studio WebSocket" 5`.
4. **Upgrade `:WaitForPort` Subroutine for Mirrored WSL2 Support:**
   Replace the `netstat -an | find "LISTENING"` check with a fast dual-mode check:
   - Primary: Fast netstat search for native Windows services.
   - Secondary / Socket Fallback: Lightweight TCP socket connection attempt via PowerShell (500ms timeout) to accurately detect listening ports inside WSL2 mirrored networking without false-positives.

---

### [Component 2] Desktop Workstation: [frontend/electron/main.js](file:///C:/AI-BS/frontend/electron/main.js)

#### [MODIFY] [main.js](file:///C:/AI-BS/frontend/electron/main.js)
1. In `spawnEcosystem()`, before spawning `brain_backend.exe` and `aibs_engine.exe`, check if ports 8080 and 8000 are already open:
   - If Port 8080 is listening, skip spawning `brain_backend.exe` and log: `[Main] Python Backend is already running on port 8080. Skipping spawn.`
   - If Port 8000 is listening, skip spawning `aibs_engine.exe` and log: `[Main] Go Gateway is already running on port 8000. Skipping spawn.`
2. In `killEcosystem()`, only attempt process termination on processes that were actually spawned by Electron and are still running.

---

### [Component 3] Architectural Ledgers & Documentation
Per strict project rules:
1. Update [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md) with timestamped entry, root-cause diagnosis, port allocations, and fallback context.
2. Update [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md), bump system version (e.g. `5.222.1` -> `5.223.0`), persist versioned snapshot to `saved_data/artifacts/YYYYMMDD_AI_BS_Master_Ecosystem_Manual.md`, and record entry in `NotebookLM_Records/artifact_history.md`.
3. Update [MASTER_HISTORICAL_INDEX.md](file:///C:/AI-BS/MASTER_HISTORICAL_INDEX.md), [MASTER_TASKS_CHRONOLOGY.md](file:///C:/AI-BS/MASTER_TASKS_CHRONOLOGY.md), and [MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md](file:///C:/AI-BS/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md).

---

## Verification Plan

### Automated & Diagnostic Tests
1. **Firewall & Batch Script Verification:**
   Run `Launch_AI_BS.bat` in a test pass to confirm:
   - Line 20 executes cleanly without `'Network' is not recognized`.
   - Ports 1935, 8089, and 8085 report `[OK] ... is online!` within 1-2 seconds.
   - Zero timeout delays from removed 8008 and 4455 probes.
2. **Comprehensive Port Scan:**
   Run `C:\AI-BS\pyppeteer_env\Scripts\python.exe C:\AI-BS\scripts\fast_scan.py` to verify all active daemons remain healthy.
3. **Electron Spawn Verification:**
   Confirm Electron launches without exit code 1 collisions.
