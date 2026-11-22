# AI-BS Project Map (Draft)

> **Evidence Labels:**
> - **from older notes:** A cited document describes an intended configuration or an earlier inventory reports an observation.
> - **verified from current source:** Checked directly in repository files or Git metadata.
> - **Observed during inventory, capture date unverified — `<source>`:** Runtime listener/PID or point-in-time state observed during inventory without a recorded capture timestamp *(capture date unresolved)*.
> - **Observed on `<timestamp>` — `<command>`:** Point-in-time observation with an explicit capture timestamp.

---

## 0. Root Repository (`C:\AI-BS`)
- **Path & Branch:** `C:\AI-BS`, branch `codex/audit-v532976-20261031`, `HEAD` `64fad2871e0a716d9964f506bdef1050612b173d` — *verified from current source* (`git -C C:\AI-BS rev-parse --abbrev-ref HEAD` and `git -C C:\AI-BS rev-parse HEAD`)
- **Working Tree Counts:**
  - Command for the two dated re-checks: `git --no-optional-locks -c core.fsmonitor=false -C C:\AI-BS status --porcelain=v1 -unormal`
  - **137** tracked-change records; **6,960** untracked paths reported in the earlier Antigravity inventory *(capture date and grouping mode unverified)*
  - **137** tracked-change records; **6,961** untracked (`??`) entries *(observed `2026-11-21T12:06:11-05:00` by Antigravity, with five permission warnings for release directories v5.329.82 through v5.329.86)*
  - **137** tracked-change records; **6,966** untracked (`??`) entries *(observed `2026-11-21T17:23:33Z` by Claude Code, which reported no warnings)*
  - *(Note: `-unormal` groups each untracked directory with no tracked files inside as a single `dir/` entry.)*
  - **Committed `AGENTS.md` Observation:** Committed `64fad2871e0a716d9964f506bdef1050612b173d:AGENTS.md` has a garbled encoding sequence (`â€”`) in the second protocol heading on L31 *(observation only, not a fix)*.

---

## 1. Backend (`AI_BS_Backend`)
- **Path:** `C:\AI-BS\backend` — *verified from current source* (`C:\AI-BS\backend\AI_BS_Backend.py`)
- **Entry Point:** Uvicorn serves `AI_BS_Backend:app` on `127.0.0.1:8080` — *verified from current source* (`backend/AI_BS_Backend.py:15526-15532`).
- **Observed Runtime:** `127.0.0.1:8080`, `python.exe` PID `41928` (`uvicorn AI_BS_Backend:app --app-dir C:\AI-BS\backend --host 127.0.0.1 --port 8080 --workers 1 --no-access-log`) — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*
- **Dependencies:** FastAPI and Uvicorn are imported in `backend/AI_BS_Backend.py:149-151`. The ChromaDB client defaults to primary port `8001` (`backend/core/memory_service.py:24`). See section 6 for the secondary store.
- **Ollama:** `ollama.exe serve`, PID `20672`, listening on `127.0.0.1:11434` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`*.
- **How to Verify:** `GET /health` and `GET /api/health` (defined in `C:\AI-BS\backend\AI_BS_Backend.py:2663-2665`); `Get-NetTCPConnection -LocalPort 8080 -State Listen`.

## 2. Frontend (`ai-bs-frontend`)
- **Path:** `C:\AI-BS\frontend` — *verified from current source* (`C:\AI-BS\frontend\package.json`)
- **Entry Point:** `npm run dev` (`vite --host 127.0.0.1 --port 5173 --strictPort`) — *verified from current source* (`C:\AI-BS\frontend\package.json`)
- **Observed Runtime:** `127.0.0.1:5173`, `node.exe` PID `33700` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*
- **Dependencies:** Node.js, Vite, React 18, Backend API (`127.0.0.1:8080`) — *verified from current source* (`C:\AI-BS\frontend\package.json`)
- **How to Verify:** `npm run build`, `npm run lint`, `npm run check:types` in `C:\AI-BS\frontend` *(found in `package.json`, untested)*; `Get-NetTCPConnection -LocalPort 5173 -State Listen`.
- **Service Status & Maintenance Limitation:**
  - `/health` -> `POST /api/tools/execute` (`get_ecosystem_health`, `Matrix Doctor`) in `ChatTab.jsx:6637-6653` — *verified from current source*
  - `/status` -> `GET /api/executive/daemons` in `ChatTab.jsx:4200-4222` (returns Unix-seconds `"timestamp": time.time()` from `daemon_manager.py:421`) — *verified from current source*
  - `/backend status` -> checks `pendingProjectMaintenance()` (`frontend/src/utils/projectMaintenance.js:17-22`), which reads **only browser `globalThis.localStorage`** under key `aibs.local-maintenance.pending.v1`. If missing, invalid, or unreadable, it returns `null` and falls back to `GET /api/health`. **Limitation:** the browser cannot detect server-wide maintenance jobs started from other browsers, origins, or CLI/agent sessions — *verified from current source*

## 3. Go Engine (`aibs_engine`)
- **Path:** `C:\AI-BS\go-core` — *Observed during inventory, capture date unverified — `Win32_Process`*
- **Entry Point:** `C:\AI-BS\go-core\aibs_engine.exe` — *Observed during inventory, capture date unverified — `Win32_Process`*
- **Observed Runtime:** `127.0.0.1:8000`, `aibs_engine.exe` PID `21780` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*
- **Dependencies:** Standalone Go binary (`aibs_engine.exe`)
- **How to Verify:** `Get-NetTCPConnection -LocalPort 8000 -State Listen`

## 4. Trading & Relay Services
- **Structural Dip Engine:**
  - **Path / Entry Point:** `C:\AI-BS\scratch\structural_dip_engine.py --role primary` — *Observed during inventory, capture date unverified — `Win32_Process`*
  - **Observed Runtime:** `127.0.0.1:8007`, `python.exe` PID `43452` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*
- **Mobile Crypto Relay:**
  - **Path / Entry Point:** `C:\AI-BS\scratch\mobile_crypto_relay.py` — *Observed during inventory, capture date unverified — `Win32_Process`*
  - **Observed Runtime:** `127.0.0.1:8017`, `python.exe` PID `29436` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*

## 5. FE Express Dispatch & Valhalla Routing Services
- **FE Express / Trip Dispatch:**
  - **Path / Entry Point:** `C:\AI-BS\backend\run_trip_dispatch.py` — *Observed during inventory, capture date unverified — `Win32_Process`*
  - **Observed Runtime:** `0.0.0.0:8025`, `python.exe` PID `16264` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*
- **Valhalla Truck Routing Service:**
  - **Path / Entry Point:** `C:\AI-BS\routing\valhalla_truck_service.py` — *Observed during inventory, capture date unverified — `Win32_Process`*
  - **Observed Runtime:** `0.0.0.0:8026`, `python.exe` PID `42512` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved)*

## 6. Chroma Store
- **Configured Ports:** Primary `8001` (`aibs_ecosystem_spawner.py:119-125`, `memory_service.py:24`, `AI_BS_Backend.py:12073`); Secondary `8002` (`aibs_ecosystem_spawner.py:129-132`) — *verified from current source*
- **Observed Runtime:** `127.0.0.1:8002`, `chroma.exe run --path E:\AI_BS_Resources\ChromaDB --port 8002 --host 127.0.0.1`, `python.exe` PID `36640` — *Observed during inventory, capture date unverified — `Get-NetTCPConnection` / `Win32_Process`* *(capture date unresolved; primary `8001` listener not observed)*

## 7. ComfyUI Bridge
- **Documented Ports:** Ports `8188/8189` — *from older notes (`C:\AI-BS\PROJECT.md:13,50`)*
- **Observed Runtime:** *Observed during inventory, capture date unverified — `Get-NetTCPConnection`*: no listener observed on 8188/8189 during inventory.

## 8. Sub-Repositories
*(Point-in-time `git status` observations during inventory, capture date unverified.)*
- **`pearl` (`C:\AI-BS\pearl`)**: `master...origin/master`, dirty (`apps/apps/pearl-desktop-wallet/resources/icon.png` unstaged).
- **`u7d42b3` (`C:\AI-BS\u7d42b3`)**: `master`, dirty (`native_app.py` unstaged).
- **`u8e53c4` (`C:\AI-BS\u8e53c4`)**: `master`, dirty (`app.py`, `native_app.py` unstaged).
- **`u9c31a2` (`C:\AI-BS\u9c31a2`)**: `master`, dirty (`app.py`, `native_app.py` unstaged).
