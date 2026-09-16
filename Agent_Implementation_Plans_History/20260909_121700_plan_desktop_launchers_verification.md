# Implementation Plan - Desktop Launchers Line-by-Line Hardening & Topology Parity (v5.230.4)

Audit, verify, and harden all three primary desktop launcher files line-by-line to ensure they reflect the consolidated single-version architecture (`C:\Program Files\AI-BS Sovereign Studio`).

## User Review Required
> [!NOTE]
> All obsolete software installations (`AI-BS Matrix` and `BS-Studio`) have been fully decommissioned, freeing >6.13 GB of disk space. All workloads (main suite, Broadcast Studio, and Wave Studio DAW) now launch exclusively from `C:\Program Files\AI-BS Sovereign Studio` and master repository `C:\AI-BS`.

## Completed Line-by-Line Inspections & Enhancements

### 1. `C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.bat` (131 lines)
- **Lines 13-31**: Locate Python Interpreter: Validated Python cascade (`%APP_DIR%pyppeteer_env` -> `C:\AI-BS\pyppeteer_env\Scripts\python.exe` -> `where python`).
- **Lines 32-96**: Daemon Readiness Checks: Verified port bindings for Go Engine (8000), FastAPI Backend (8080), VST Bridge (8013), Social Feed Daemon (8006), and Broadcast Engine (8005).
- **Lines 97-107**: Local Desktop Server: Probes Port 5173 and starts `serve_desktop.py 5173` using non-blocking headless ping delays (`ping 127.0.0.1 -n 3 >nul`).
- **Lines 109-126**: Application Window: Launches isolated Edge/Chrome application window with `--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173`.

### 2. `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` (77 lines)
- **Lines 13-31**: Locate Python Interpreter: Injected comprehensive Python cascade matching `Launch_Desktop_Studio.bat`.
- **Lines 32-41**: Broadcast Kernel on 8088: Probes Port 8088 and falls back to `C:\AI-BS\backend\aibs_broadcast_kernel.py` if missing from local directory.
- **Lines 43-54**: Broadcast UI Server on 5174: Probes Port 5174, launches `serve_desktop.py 5174`, and uses non-blocking ping delays.
- **Lines 55-73**: Dedicated Broadcast & DAW Window: Injected `--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5174,http://localhost:5174 --use-fake-ui-for-media-stream` so Edge/Chrome does not block webcam, microphone, or WebRTC streaming.

### 3. `C:\AI-BS\Launch_AI_BS.bat` (166 lines)
- **Lines 90-99**: Native App Priority: Updated to check and prioritize installed production binary `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` first before local dev builds. Excised dead path `E:\AI-BS Broadcast Studio\AI-BS Broadcast Studio.exe`.
- **Lines 101-135**: Parallel Background Monitor: Probes all 18 core services and pre-warms Stehouwer LLM on RTX 4090.

### 4. `serve_desktop.py` (Installer & Program Files)
- Re-engineered `determine_serve_dir(port, custom_dir)`:
  - Port 5173 -> Serves `frontend_dist` or `C:\AI-BS\frontend\dist`
  - Port 5174 -> Serves `broadcast_dist` or `C:\AI-BS\BroadcastStudioApp\dist`

### 5. `C:\AI-BS\Shutdown_AI_BS.bat`
- Added process kill directive for `AI-BS Sovereign Studio.exe`.

## Verification Plan
- [x] Test port directory resolution logic in Python (5173 -> frontend_dist, 5174 -> broadcast_dist)
- [x] Verify shortcut target paths on desktop via Windows Script Host COM object
- [x] Sweep version badges to `v5.230.4`, strip UTF-8 BOM, and compile with Vite
- [x] Deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`)
- [x] Robocopy mirrored fresh bundle to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`
