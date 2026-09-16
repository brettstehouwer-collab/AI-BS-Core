# Implementation Plan: Electron / Go / React BTD6 Memory Trainer Pipeline

Build a native desktop version of the Bloons TD 6 Memory Trainer integrating an Electron container, a compiled Go high-speed Win32 memory daemon, and a modern React 19 / TypeScript user interface communicating over dedicated IPC pipelines.

---

## 1. System Architecture & Communication Pipeline

```
+-------------------------------------------------------------------------+
|                  Electron Desktop Window (Frameless)                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |             React 19 / TypeScript UI (Renderer Process)           |  |
|  |  - Custom Drag Titlebar & Window Controls (Min / Max / Close)     |  |
|  |  - 🎯 Memory Scanner (Presets $650/$850/$450/$1750, Next Scan)    |  |
|  |  - ⚡ Match Cheats Grid (F1-F7, F10 Dual-Bound Toggles)           |  |
|  |  - 🎛️ Variables & Steppers (Cash, Lives, Monkey Money)          |  |
|  |  - 📊 Live Daemon Telemetry & Verification Event Log              |  |
|  +-------------------------------------------------------------------+  |
|                                   │                                     |
|             window.api (Preload IPC Bridge via contextBridge)           |
|                                   ▼                                     |
|  +-------------------------------------------------------------------+  |
|  |                 Electron Main Process (Node.js)                   |  |
|  |  - Spawns & monitors compiled Go Daemon (windowsHide: true)       |  |
|  |  - Bridges JSON-lines stdin / stdout over IPC                    |  |
|  |  - Manages frameless window actions (minimize, maximize, close)   |  |
|  +-------------------------------------------------------------------+  |
+-----------------------------------│-------------------------------------+
                                    │ stdio JSON IPC (line-delimited)
                                    ▼
+-------------------------------------------------------------------------+
|                Go Native Memory Engine & Daemon (amd64)                 |
|  +-------------------------------------------------------------------+  |
|  |  - Win32 API: OpenProcess, VirtualQueryEx, Read/WriteProcessMemory|  |
|  |  - Strict 8-byte alignment (Double) & 4-byte alignment (Int32)    |  |
|  |  - 2MB memory chunk scanner with boundary overlap                 |  |
|  |  - Two-stage candidate filtering: FirstScan -> NextScan (<1ms)   |  |
|  |  - Decoupled 25ms continuous tick freeze loop (0% idle CPU)       |  |
|  |  - Automatic background process discovery for BloonsTD6.exe      |  |
|  +-------------------------------------------------------------------+  |
|                                   │                                     |
|                                   ▼                                     |
|                    Target Process: BloonsTD6.exe                        |
+-------------------------------------------------------------------------+
```

---

## 2. Component Specifications

### Component A: Go Native Memory Engine & Daemon
- **Target File:** `go-core/cmd/btd6_trainer_daemon/main.go`
- **Output Binary:** `trainer_frontend/resources/btd6_trainer_daemon.exe` and `C:\AI-BS\EXE\btd6_trainer_daemon.exe`
- **Responsibilities:**
  1. **Win32 Memory API:**
     - Bind `kernel32.dll` via `syscall.NewLazyDLL`: `OpenProcess`, `CloseHandle`, `ReadProcessMemory`, `WriteProcessMemory`, `VirtualQueryEx`, `CreateToolhelp32Snapshot`, `Process32FirstW`, `Process32NextW`.
  2. **Memory Scanner & Alignment:**
     - Scan committed memory regions (`PAGE_READWRITE`) in 2MB buffer chunks with boundary overlap.
     - Enforce `addr % 8 == 0` for `float64` (double match cash & lives) and `addr % 4 == 0` for `int32` (Monkey Money).
  3. **Candidate Filtering Pipeline:**
     - `FirstScanCash(targetVal)`: Traverses committed RAM, extracts all aligned matching addresses into `cashCandidates`.
     - `NextScanCash(newVal)`: Re-reads only the addresses in `cashCandidates` in <1ms, retaining addresses matching `newVal`. When count drops to $\le 8$, auto-locks to `lockedCashAddrs` and engages unlimited cash freeze.
     - `FirstScanCoins(val)` & `NextScanCoins(val)`: Same multi-stage narrowing for int32 Monkey Money.
  4. **Decoupled Tick Loop:**
     - 25ms ticker loops exclusively write frozen values to `lockedCashAddrs` and `lockedCoinsAddrs` without invoking memory scans.
  5. **JSON IPC Protocol (over stdio):**
     - **Incoming Commands (stdin):**
       - `{"action": "first_scan_cash", "value": 650.0}`
       - `{"action": "next_scan_cash", "value": 684.0}`
       - `{"action": "add_cash", "amount": 50000.0}`
       - `{"action": "first_scan_coins", "value": 1500}`
       - `{"action": "next_scan_coins", "value": 1520}`
       - `{"action": "set_coins", "value": 99999}`
       - `{"action": "toggle_feature", "feature": "Unlimited Match Cash"}`
       - `{"action": "set_variable", "variable": "frozen_cash_val", "value": 99999.0}`
       - `{"action": "quit"}`
     - **Outgoing State Events (stdout):**
       - `{"type": "state_update", "status": "ATTACHED"|"SEARCHING", "pid": 1234, "cash_locked": true, "cash_addresses": ["0x..."], "cash_candidates_count": 2, "coins_locked": false, "coins_candidates_count": 0, "features": {...}, "variables": {...}}`
       - `{"type": "log", "level": "info"|"warn"|"error", "message": "..."}`

---

### Component B: Electron Main & Preload Process
- **Target Files:**
  - `trainer_frontend/src/main/index.ts`
  - `trainer_frontend/src/preload/index.ts`
  - `trainer_frontend/src/preload/index.d.ts`
- **Responsibilities:**
  1. **Daemon Spawner:**
     - Prioritize running `btd6_trainer_daemon.exe` (from `resourcesPath` in production or `resources/` / `go-core` in dev).
     - Fall back to Python daemon if the Go binary is not found.
  2. **Frameless Window Controls:**
     - Configure BrowserWindow with `frame: false`, `titleBarStyle: 'hidden'`, `transparent: false`, `backgroundColor: '#0a0d14'`.
     - Register IPC handlers for `window-minimize`, `window-maximize`, `window-close`, `is-window-maximized`.
  3. **IPC Bridge:**
     - Provide typed APIs in `window.api`:
       - `sendDaemonCommand(cmd)`
       - `onDaemonMessage(callback)`
       - `minimizeWindow()`, `maximizeWindow()`, `closeWindow()`, `openExternal(url)`

---

### Component C: React UI Renderer Layer
- **Target Files:**
  - `trainer_frontend/src/renderer/src/App.tsx`
  - `trainer_frontend/src/renderer/src/assets/main.css`
  - `trainer_frontend/src/renderer/src/components/ScannerDeck.tsx` [NEW]
  - `trainer_frontend/src/renderer/src/components/CheatsDeck.tsx` [NEW]
  - `trainer_frontend/src/renderer/src/components/VariablesDeck.tsx` [NEW]
  - `trainer_frontend/src/renderer/src/components/TelemetryLog.tsx` [NEW]
- **Responsibilities:**
  1. **Cyberpunk Frameless Header:**
     - Drag region, AI-BS Cyber Dart Monkey icon, window status badge (`● ATTACHED (PID 26496)` / `◌ SEARCHING FOR GAME...`), Steam Launch button (`steam://rungameid/960090`), and window control buttons (`_`, `□`, `✕`).
  2. **Tabbed Navigation:**
     - `🎯 Scanner` (Multi-stage calibration with starting cash presets: `$650`, `$850`, `$450`, `$1750`, First/Next scan, live candidate badge).
     - `⚡ Cheats` (F1-F7, F10 dual-bound quick keys with active glow and slider toggles).
     - `🎛️ Variables` (Direct value setters and limit steppers).
     - `📊 Telemetry` (Real-time memory operations stream and scan diagnostics).

---

## 3. Verification Plan

### Automated Tests
1. **Go Daemon Standalone Test:**
   - Execute an automated test (`tests/test_go_trainer_daemon.py` or Go unit test) verifying:
     - Spawning `btd6_trainer_daemon.exe`.
     - Sending `first_scan_cash` command and receiving formatted JSON state update over stdout.
     - Sending feature toggle and variable commands.
     - Clean termination on `quit`.
2. **Electron & React Build:**
   - Run `npm run typecheck` in `trainer_frontend`.
   - Run `npm run build` (`electron-vite build`).
   - Run `npm run build:unpack` (`electron-builder --dir`) to generate the native unpacked Windows application.
3. **Parity & Ledger Sync:**
   - Verify `version.txt` and manifests bumped to `5.249.0`.
   - Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.

---

## 4. User Review Required

> [!IMPORTANT]
> The Go memory engine will be compiled as a standalone 64-bit Windows binary (`btd6_trainer_daemon.exe`). It executes with full native speed and zero Python runtime dependencies. The Electron application directly bundles and launches this Go binary through its stdio JSON IPC pipeline.

Please confirm whether you would like to proceed with the execution of this plan.
