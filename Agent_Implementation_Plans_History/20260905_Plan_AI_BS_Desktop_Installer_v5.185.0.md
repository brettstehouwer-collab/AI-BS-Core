# Implementation Plan: AI-BS Sovereign Studio Windows Desktop Installer (v5.185.0)

Package the complete AI-BS Sovereign Intelligence & Studio Suite into a single, professional, high-performance Windows desktop installer (`AI_BS_Studio_Setup_v5.185.0.exe`) for full functional local use of everything across Windows 10 & 11.

## User Review Required

> [!IMPORTANT]
> - **100% Free, Open-Source & Local:** Uses Jordan Russell's Inno Setup 6.7.3 compiler (`ISCC.exe`) installed locally on the system. Zero third-party paid licensing or telemetry.
> - **Full Functional Local Use of Everything:** Bundles the complete pre-built production frontend (`frontend/dist`), the Broadcast Studio App (`BroadcastStudioApp/dist`), the core Python FastAPI server (`AI_BS_Backend.py`), the Go commercial gateway (`go-core/aibs_engine.exe`), the multi-threaded broadcast daemons, audio routers, and desktop runners.
> - **Zero-Setup Desktop App Experience:** Includes an embedded Python SPA web server and headless desktop app launcher that opens AI-BS Studio in dedicated standalone window mode (`--app=http://127.0.0.1:5173`) with custom icon, WebGL, Web Audio, and microphone recording enabled.
> - **System Integration:** Automatically configures Windows Desktop shortcuts, Start Menu program groups, custom `.aibs`, `.daw`, and `.stehouwer` file associations, and standard Windows Control Panel uninstaller.

---

## Proposed Changes

### Installer Architecture & Desktop Runner Layer

#### [NEW] [installer/serve_desktop.py](file:///C:/AI-BS/installer/serve_desktop.py)
- High-performance, lightweight local HTTP server built using Python's `http.server`.
- Features:
  - Serves static files from the bundled `frontend_dist/` directory.
  - SPA fallback routing: redirects non-file requests to `index.html` for client-side routing.
  - Custom MIME types for `.js`, `.mjs`, `.css`, `.svg`, `.wasm`, `.woff2`, `.json`.
  - Binds cleanly to `127.0.0.1:5173` (or falls back to an open port if 5173 is occupied).

#### [NEW] [installer/Launch_Desktop_Studio.bat](file:///C:/AI-BS/installer/Launch_Desktop_Studio.bat)
- Complete launcher script executed when the user double-clicks the desktop shortcut:
  1. Checks if the backend FastAPI engine (`port 8000`), Go gateway (`port 8080`), and Broadcast Kernel (`port 8088`) are running; if not, starts them silently in the background.
  2. Starts the local frontend web server (`serve_desktop.py`) on port 5173.
  3. Launches Microsoft Edge or Google Chrome in dedicated application window mode:
     `msedge.exe --app=http://127.0.0.1:5173 --window-size=1600,1000 --user-data-dir="%LOCALAPPDATA%\AI-BS_Studio\BrowserProfile"`
  4. Delivers a native, clean desktop window with full hardware acceleration, microphone access for Stehouwer Wave Studio, and zero browser toolbar distraction.

#### [NEW] [installer/Launch_Desktop_Studio.vbs](file:///C:/AI-BS/installer/Launch_Desktop_Studio.vbs)
- VBScript wrapper to launch `Launch_Desktop_Studio.bat` completely silently without showing a flashing command prompt window.

#### [NEW] [installer/Launch_Broadcast_Studio.bat](file:///C:/AI-BS/installer/Launch_Broadcast_Studio.bat)
- Dedicated launcher for the Broadcast Studio workstation (port 5174 / Electron / Web App).

#### [NEW] [installer/Shutdown_Desktop_Studio.bat](file:///C:/AI-BS/installer/Shutdown_Desktop_Studio.bat)
- Graceful shutdown script that terminates background daemons, servers, and cleans memory.

---

### Inno Setup 6 Script & Automated Build Pipeline

#### [NEW] [installer/AI_BS_Studio_Setup.iss](file:///C:/AI-BS/installer/AI_BS_Studio_Setup.iss)
- Comprehensive Inno Setup 6 compiler script:
  - App Name: `AI-BS Sovereign Intelligence Studio`
  - App Version: `5.185.0`
  - Publisher: `Brett Stehouwer / Stehouwer Publishing`
  - Default Installation Directory: `{autopf}\AI-BS Sovereign Studio` (with user option to customize).
  - Compression: `lzma2/ultra64` with solid compression for optimal disk footprint.
  - Files to Package:
    - Production UI: `frontend/dist/**/*` -> `{app}\frontend_dist`
    - Broadcast Studio UI: `BroadcastStudioApp/dist/**/*` -> `{app}\broadcast_dist`
    - Backend Daemons & Routers: `backend/*.py`, `backend/server.js`, `backend/requirements.txt` -> `{app}\backend`
    - Go Commercial Gateway: `go-core/aibs_engine.exe` -> `{app}\go-core`
    - Launchers & Runners: `Launch_AI_BS.bat`, `Shutdown_AI_BS.bat`, `Launch_Desktop_Studio.bat`, `serve_desktop.py`, etc. -> `{app}`
    - Custom Branding & Icons: `build/icon.ico` -> `{app}`
  - Windows Shortcuts:
    - Desktop: `AI-BS Sovereign Studio`, `AI-BS Broadcast Studio`, `AI-BS Matrix Boot`, `AI-BS Shutdown`
    - Start Menu: `AI-BS Sovereign Studio` program group containing all launchers and documentation.
  - Registry & File Associations:
    - `.aibs` -> AI-BS Master Project
    - `.daw` -> AI-BS Neural DAW Track
    - `.stehouwer` -> Stehouwer Wave Audio Session
  - Post-Install Option: "Launch AI-BS Sovereign Studio immediately".

#### [NEW] [installer/build_desktop_installer.ps1](file:///C:/AI-BS/installer/build_desktop_installer.ps1)
- Automated PowerShell script to execute `ISCC.exe` on `AI_BS_Studio_Setup.iss`, verify the generated binary, and mirror it to `C:\AI-BS\InstallerEXE's\AI_BS_Studio_Setup_v5.185.0.exe`.

---

### Version Parity & Live Deployment

#### [MODIFY] Version Badges to v5.185.0:
- `frontend/src/components/TopNavbar.jsx`
- `frontend/src/components/ChatTab.jsx`
- `frontend/src/components/PhoneRepairGuideTab.jsx`
- Parity mirrors across:
  - `frontend/src/components/components/`
  - `frontend/components/`
  - `frontend/components/components/`

#### Live Firebase Deployment:
- Execute `npm run build; firebase deploy --only hosting --non-interactive` from `frontend/`.

---

### Master Documentation Synchronization
- Update `C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` with timestamped `v5.185.0` entry detailing the Desktop Installer architecture.
- Update `C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (bump to `5.185.0`) and persist copy to `saved_data/artifacts/20260905_AI_BS_Master_Ecosystem_Manual_v5.185.0.md`.
- Update `NotebookLM_Records/artifact_history.md`, `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.

---

## Verification Plan

### Automated Tests & Builds
- Run `build_desktop_installer.ps1` to compile `AI_BS_Studio_Setup_v5.185.0.exe` using Inno Setup 6.
- Verify exit code `0` and verify the `.exe` file exists with valid size (>10 MB).
- Run `npm run build` in `frontend/` to ensure production bundle compiles cleanly.
- Verify live Firebase deployment responds with `200 OK` at `https://ai-bs-dashboard.web.app`.

### Manual / System Verification
- Inspect the generated installer file properties, version string (`5.185.0`), and digital publisher info.
- Verify test launch of `serve_desktop.py` and desktop launcher script.
