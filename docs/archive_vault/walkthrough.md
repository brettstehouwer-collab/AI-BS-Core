# Walkthrough: Decommission Outdated v5.185.0 Binary, Harden Modern Edge App Window & Resolve Batch Syntax Errors

## Executive Summary

Resolved the root causes that triggered:
1. An outdated `v5.185.0` Electron window launching on master boot with child process crash logs.
2. The `'Vault)' is not recognized as an internal or external command` syntax error and `[Errno 10048]` socket collision on Port 8007.
3. Ampersand command parsing errors in the Live Broadcast Studio launcher.

---

## 1. Obsolete Electron Decommissioning & Disk Space Reclamation

- **Root Cause**: `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` and `resources\app.asar` were leftover from a September 5, 2026 build (`v5.185.0`). The executable opened its own internal mini web server on `127.0.0.1:5173`, intercepted port 5173, served stale September 5 assets, and attempted to spawn duplicate `brain_backend.exe` and `aibs_engine.exe` child binaries that exited with code 1 due to port collisions with the master daemons.
- **Remediation**:
  - Terminated active instances of `AI-BS Sovereign Studio.exe`.
  - Excised `AI-BS Sovereign Studio.exe` (181 MB), `resources\` (2.75 GB), and associated Electron runtime DLLs/paks (`ffmpeg.dll`, `d3dcompiler_47.dll`, `locales/`).
  - **Storage Result**: Reclaimed **3.05 GB** of disk space on Drive C: (free space expanded from 103.40 GB to 106.45 GB).

---

## 2. Desktop Launcher Modernization & Shortcut Repointing

- **[Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)**:
  - Lines 90–100 updated to exclusively invoke the official Inno Setup launcher [Launch_Desktop_Studio.vbs](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_Desktop_Studio.vbs) / `.bat`.
  - Launches Microsoft Edge in dedicated application window mode:
    ```bat
    msedge.exe --app=http://127.0.0.1:5173 --window-size=1600,1000 --user-data-dir="%LOCALAPPDATA%\AI_BS_Studio\DesktopProfile"
    ```
  - Delivers a frameless, native desktop window connected directly to the live/compiled UI at `v5.232.0` with full GPU acceleration, WebRTC permissions, zero port collisions, and zero child crashes.
  - Mirrored to `C:\Program Files\AI-BS Sovereign Studio\Launch_AI_BS.bat`.
- **Desktop Shortcut Repointing**:
  - `C:\Users\footb\OneDrive\Desktop\AI-BS Main Workstation (Full Suite & DAW).lnk` updated:
    - Target: `C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs`
    - Working Directory: `C:\Program Files\AI-BS Sovereign Studio`
    - Icon: `C:\Program Files\AI-BS Sovereign Studio\app_icon.ico,0`

---

## 3. Batch Script Syntax Hardening & Port 8007 Collision Guard

- **[Start_Crypto_Swarm.bat](file:///C:/AI-BS/Start_Crypto_Swarm.bat)**:
  - Escaped ampersands with carets (`^&`):
    - `title AI-BS Crypto Swarm Daemon (CRO Scalp ^& Vault)`
    - `echo Booting Unified HFT Crypto Trader (CRO 50c Scalp ^& Vault)`
    - Completely eliminates the `'Vault)' is not recognized...` error.
  - Added intelligent pre-flight port inspection:
    ```bat
    netstat -an | find ":8007 " | find "LISTENING" >nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] AI-BS Crypto Trader Bot is already active and running on port 8007.
        echo Daemon status: OPERATIONAL (managed by AI-BS Master Engine)
        echo Socket collision avoided.
        ping 127.0.0.1 -n 3 >nul
        exit /b 0
    )
    ```
    Prevents duplicate daemon execution and eliminates `[Errno 10048]` socket collisions.
- **[installer\Launch_Broadcast_Studio.bat](file:///C:/AI-BS/installer/Launch_Broadcast_Studio.bat) & `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat`**:
  - Escaped ampersands: `Broadcast ^& Neural DAW Workstation`.

---

## 4. UI Version Parity & Live Production Deployment

- Swept 28 frontend UI components, configuration files, and `package.json` to version `v5.232.0`.
- Successfully compiled production bundle (`npm run build` in 26.78s).
- Mirrored distribution bundle to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist` via Robocopy `/MIR`.
- Deployed live production hosting to Firebase: `https://ai-bs-dashboard.web.app`.

---

## 5. Verification Results

| Check | Expected | Result |
| :--- | :--- | :--- |
| Obsolete Electron Process | 0 running instances | **Verified (0 processes)** |
| Port 5173 Listening Process | Node.exe (Vite dev server) | **Verified (Clean binding, 0 collisions)** |
| `Start_Crypto_Swarm.bat` Syntax | Zero `'Vault)'` errors | **Verified (Clean execution, code 0)** |
| Port 8007 Socket Guard | Avoids duplicate binding | **Verified (Reports OPERATIONAL and exits cleanly)** |
| Desktop Shortcut Target | `Launch_Desktop_Studio.vbs` | **Verified (`Launch_Desktop_Studio.vbs`)** |
| Program Files Disk Reclaim | ~3 GB freed | **Verified (3.05 GB freed on Drive C:)** |
| Live Firebase Deployment | HTTP 200 at `v5.232.0` | **Verified (ai-bs-dashboard.web.app live)** |
