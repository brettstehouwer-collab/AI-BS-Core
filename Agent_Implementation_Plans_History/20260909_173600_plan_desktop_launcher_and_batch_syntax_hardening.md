# Implementation Plan: Decommission Outdated v5.185.0 Binary, Fix Crypto Swarm Port 8007 Collision & Batch Ampersand Syntax

## Forensic Root Cause Analysis

Two distinct issues were identified from the startup logs and operator terminal trace:

### Issue 1: Outdated Windows Desktop Program Spawns on Master Boot
```
[Main] Spawning Python Backend: C:\Program Files\AI-BS Sovereign Studio\resources\brain_backend\brain_backend.exe
[Main] Spawning Go Gateway: C:\Program Files\AI-BS Sovereign Studio\resources\go-core\aibs_engine.exe
[UI Server] Serving dist from http://127.0.0.1:5173
[Main] Go Gateway exited — code: 1, signal: null
[Main] Python Backend exited — code: 1, signal: null
```
1. **Source of the Outdated Window**:
   - `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` is a frozen Electron binary packaged on **September 5, 2026** (`v5.185.0`).
   - Inside its bundled `resources\app.asar` (796 MB), it embeds obsolete September 5th React frontend bundle assets.
   - When executed, Electron's internal script runs `startLocalUiServer()` on `127.0.0.1:5173`, binding to the loopback interface and serving its stale `v5.185.0` assets.
   - It also executes redundant child processes `brain_backend.exe` and `aibs_engine.exe` from `C:\Program Files\AI-BS Sovereign Studio\resources\` (2.75 GB), which immediately crash with exit code 1 because ports 8000 and 8080 are already running under master supervision.
2. **Why `Launch_AI_BS.bat` Spawned It**:
   - Lines 91–99 in `Launch_AI_BS.bat` prioritized checking for and launching `C:\Program Files\AI-BS Sovereign Studio\AI-BS Sovereign Studio.exe` before the modern script launcher.
3. **Desktop Shortcut Repointing**:
   - `AI-BS Main Workstation (Full Suite & DAW).lnk` on `C:\Users\footb\OneDrive\Desktop` also targets `AI-BS Sovereign Studio.exe`.
4. **Standard Ecosystem Architecture**:
   - The official application launcher is `Launch_Desktop_Studio.vbs` / `Launch_Desktop_Studio.bat`, which launches Microsoft Edge in dedicated application window mode (`--app=http://127.0.0.1:5173`), connecting directly to the live/compiled UI at `v5.231.0` with zero port collisions and full GPU acceleration.

---

### Issue 2: `'Vault)' is not recognized...` & WinError 10048 Port 8007 Collision
```
'Vault)' is not recognized as an internal or external command,
operable program or batch file.
========================================================
Booting Unified HFT Crypto Trader (CRO 50c Scalp
'Vault)' is not recognized as an internal or external command,
operable program or batch file.
Target Port: 8007
========================================================
ERROR:    [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8007): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted
```
1. **Root Cause of `'Vault)' is not recognized...`**:
   - In `C:\AI-BS\Start_Crypto_Swarm.bat`:
     - Line 2: `title AI-BS Crypto Swarm Daemon (CRO Scalp & Vault)`
     - Line 5: `echo Booting Unified HFT Crypto Trader (CRO 50c Scalp & Vault)`
   - In Windows `cmd.exe`, the unescaped `&` acts as a command chaining operator. The shell attempts to execute `Vault)` as a separate command, raising `'Vault)' is not recognized as an internal or external command`.
   - The same unescaped `&` pattern exists in `installer\Launch_Broadcast_Studio.bat` and `C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat` (`title AI-BS Broadcast & DAW Workstation` -> `'DAW' is not recognized`).
2. **Root Cause of `[Errno 10048]` (Address in use)**:
   - `Launch_AI_BS.bat` already boots `crypto_trader_bot.py` on Port 8007 in the background (Line 79: `aibs_crypto_trader_bot` verified `[OK] on 8007`).
   - When `Start_Crypto_Swarm.bat` (or its desktop shortcut `Start Crypto Swarm.lnk`) is launched, it attempts to bind a second instance of `uvicorn` to `0.0.0.0:8007` without a pre-flight port check, triggering `[Errno 10048]`.

---

## User Review Required

> [!IMPORTANT]
> **Action Plan**:
> 1. Decommission and remove the obsolete 2.75 GB `resources\` directory and `AI-BS Sovereign Studio.exe` in `C:\Program Files\AI-BS Sovereign Studio\`.
> 2. Repoint `Launch_AI_BS.bat` and desktop shortcut `AI-BS Main Workstation (Full Suite & DAW).lnk` to modern [Launch_Desktop_Studio.vbs](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_Desktop_Studio.vbs).
> 3. Escape all unescaped ampersands (`^&`) across `Start_Crypto_Swarm.bat` and `Launch_Broadcast_Studio.bat`.
> 4. Add an intelligent pre-flight port check to `Start_Crypto_Swarm.bat` so it reports active daemon health instead of crashing if Port 8007 is already running.

---

## Proposed Changes

### 1. Process Termination
- Kill running `AI-BS Sovereign Studio.exe` process (PID 43520) and any orphaned Electron child processes.

### 2. Boot Launcher Hardening
#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat) & [C:\Program Files\AI-BS Sovereign Studio\Launch_AI_BS.bat](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_AI_BS.bat)
- Replace lines 90–100 to launch `Launch_Desktop_Studio.vbs` (or `.bat`) instead of `AI-BS Sovereign Studio.exe`.

### 3. Desktop Shortcut Repointing
- Repoint `C:\Users\footb\OneDrive\Desktop\AI-BS Main Workstation (Full Suite & DAW).lnk`:
  - TargetPath: `C:\Program Files\AI-BS Sovereign Studio\Launch_Desktop_Studio.vbs`
  - WorkingDirectory: `C:\Program Files\AI-BS Sovereign Studio`
  - IconLocation: `C:\Program Files\AI-BS Sovereign Studio\app_icon.ico,0`

### 4. Storage Reclamation & Decommissioning
- Remove obsolete `AI-BS Sovereign Studio.exe` (181 MB) and `resources\` (2.75 GB) from `C:\Program Files\AI-BS Sovereign Studio\`, freeing **~2.92 GB** on Drive C:.

### 5. Batch Syntax & Port Collision Hardening
#### [MODIFY] [Start_Crypto_Swarm.bat](file:///C:/AI-BS/Start_Crypto_Swarm.bat)
- Escape ampersands: `title ... (CRO Scalp ^& Vault)` and `echo ... (CRO 50c Scalp ^& Vault)`.
- Add pre-flight port 8007 inspection: if active, print status cleanly and exit without socket crash.
#### [MODIFY] [installer\Launch_Broadcast_Studio.bat](file:///C:/AI-BS/installer/Launch_Broadcast_Studio.bat) & [C:\Program Files\AI-BS Sovereign Studio\Launch_Broadcast_Studio.bat](file:///C:/Program%20Files/AI-BS%20Sovereign%20Studio/Launch_Broadcast_Studio.bat)
- Escape ampersands in `title` and `echo` statements (`Broadcast ^& Neural DAW Workstation`).

### 6. Architectural Ledger & System Manual Version Bump
- Log timestamped entry `5.232.0` in [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md).
- Update [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md), persist artifact copy to `saved_data/artifacts/20260909_AI_BS_Master_Ecosystem_Manual.md`, and log in `NotebookLM_Records/artifact_history.md`.
- Update chronologies and historical index.

---

## Verification Plan

### Automated Verification
1. **Batch Syntax Check**: Execute `Start_Crypto_Swarm.bat` while Port 8007 is active to verify zero `'Vault)'` errors and clean operational status output.
2. **Shortcut Verification**: Query WScript.Shell TargetPath of `AI-BS Main Workstation (Full Suite & DAW).lnk`.
3. **Port 5173 Check**: Verify `http://127.0.0.1:5173/version.json` responds cleanly without Electron port interception.
4. **Storage Audit**: Verify disk space reclaimed in `C:\Program Files\AI-BS Sovereign Studio`.

### Manual Verification
1. Run `Launch_Desktop_Studio.bat` to confirm Edge App Window opens cleanly at current system version `v5.232.0`.
