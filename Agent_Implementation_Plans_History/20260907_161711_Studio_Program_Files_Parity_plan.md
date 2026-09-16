# Verification & Synchronization Plan: C:\Program Files\AI-BS Sovereign Studio (v5.199.0)

A diagnostic audit of the installed desktop application at `C:\Program Files\AI-BS Sovereign Studio` was performed against the master codebase `C:\AI-BS` (v5.199.0). 

## Audit Findings: Is Everything Up To Date?

**Verdict: Partially.** The frontend single-page application, Go engine core, and updater executable are up to date, but the Python backend daemons, routers, telemetry data, update manifests, and architectural manuals inside `C:\Program Files\AI-BS Sovereign Studio` are out of date or missing.

### Detailed Component Parity Breakdown

| Component / File | Installed Path | Current Status | Audit Details |
| :--- | :--- | :--- | :--- |
| **Frontend SPA Bundle** | `frontend_dist\index.html` | ✅ **UP TO DATE** | 2,331 bytes, compiled with v5.199.0 assets |
| **Frontend JS Modules** | `frontend_dist\js\main.C7dr6qjE.js` | ✅ **UP TO DATE** | Contains Pearl payout card, $53.42 debit logic |
| **Go Gateway Core** | `go-core\aibs_engine.exe` | ✅ **UP TO DATE** | SHA256: `A8B5C238EE3C49344E7C67014508FB...` |
| **In-Place Updater Stub** | `aibs_updater.exe` | ✅ **UP TO DATE** | SHA256: `68EA8F5F88FF22F781E5B465507678...` |
| **Desktop Launcher** | `Launch_Desktop_Studio.bat` | ✅ **UP TO DATE** | 6,567 bytes |
| **Desktop Updater Script** | `Update_Desktop_Studio.bat` | ✅ **UP TO DATE** | 5,244 bytes |
| **Desktop Static Server** | `serve_desktop.py` | ✅ **UP TO DATE** | 4,027 bytes (SPA router on port 5173) |
| **Backend Core Server** | `backend\AI_BS_Backend.py` | ❌ **OUT OF DATE** | Installed: 217,815 bytes (9/5). Source: 224,597 bytes (9/7) |
| **GPU Network Router** | `backend\commercial_gateway\` | ❌ **MISSING** | Missing `gpu_network_router.py` (Pearl payout debit) |
| **Updater Router** | `backend\routers\` | ❌ **MISSING** | Missing `updater_router.py` (port 8080 check & payload) |
| **Pearl Router** | `backend\pearl_router.py` | ❌ **MISSING** | Missing Pearl pool proxy & telemetry router |
| **Compute Telemetry** | `backend\compute_telemetry.json` | ❌ **OUT OF DATE** | Stale un-debited state ($0.00 redeemed vs $53.42) |
| **Pearl Payout Ledger** | `backend\pearl_payout_ledger.json` | ❌ **MISSING** | Missing persistent payout receipt `tx-prl-1788810893` |
| **Update Manifest** | `frontend_dist\updates\version.json` | ❌ **OUT OF DATE** | Contains old SHA256 (`0fd598...` vs `4ef3e3...`) |
| **Frontend Version File** | `frontend_dist\version.json` | ❌ **OUT OF DATE** | Contains legacy `"version": "1.6.2"` |
| **Master Arch Ledger** | `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` | ❌ **OUT OF DATE** | Installed: 494 KB (9/5). Source: 564 KB (v5.199.0) |
| **Ecosystem Manual** | `docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md` | ❌ **OUT OF DATE** | Installed: 147 KB (9/5). Source: 185 KB (v5.199.0) |

---

## User Review Required

> [!IMPORTANT]
> Because `C:\Program Files\AI-BS Sovereign Studio` is located in Windows `Program Files`, file modifications require administrator privileges or execution from an elevated session. The in-place updater script (`Update_Desktop_Studio.bat`) handles UAC elevation automatically, or files can be synchronized directly via administrator PowerShell.

> [!NOTE]
> When running the desktop application via `Launch_Desktop_Studio.bat`:
> - If port 8080 is already active (running the main development backend from `C:\AI-BS\backend`), the desktop app communicates with the live up-to-date backend seamlessly.
> - However, if the desktop app is launched standalone without the dev backend running, it attempts to launch the installed backend in `C:\Program Files\AI-BS Sovereign Studio\backend\AI_BS_Backend.py`. Without the missing routers (`commercial_gateway`, `routers`, `pearl_router.py`), standalone startup would encounter import errors.

---

## Proposed Changes & Synchronization Plan

### 1. Backend Core & Router Synchronization
- Synchronize `C:\AI-BS\backend\AI_BS_Backend.py` to `C:\Program Files\AI-BS Sovereign Studio\backend\AI_BS_Backend.py`.
- Copy directory `C:\AI-BS\backend\commercial_gateway\` into `C:\Program Files\AI-BS Sovereign Studio\backend\commercial_gateway\`.
- Copy directory `C:\AI-BS\backend\routers\` into `C:\Program Files\AI-BS Sovereign Studio\backend\routers\`.
- Copy `C:\AI-BS\backend\pearl_router.py`, `C:\AI-BS\backend\compute_telemetry.json`, and `C:\AI-BS\backend\pearl_payout_ledger.json` into `C:\Program Files\AI-BS Sovereign Studio\backend\`.

### 2. Version Manifests & Update Check Alignment
- Synchronize `C:\AI-BS\frontend\public\updates\version.json` (SHA256: `4ef3e383ea8fade33228321de3583e9ec81be639d42d8c18ca2749189db6cb99`, size 887,352,835 bytes) to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist\updates\version.json`.
- Update `C:\Program Files\AI-BS Sovereign Studio\frontend_dist\version.json` and `C:\AI-BS\frontend\public\version.json` to reflect `"version": "5.199.0"`.

### 3. Documentation & Architectural Ledgers Parity
- Synchronize `C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` to `C:\Program Files\AI-BS Sovereign Studio\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
- Synchronize `C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md` to `C:\Program Files\AI-BS Sovereign Studio\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.

### 4. Installer & Updater Delta Packaging Script Enhancement
- Update `C:\AI-BS\scripts\package_update_payload.ps1` and `C:\AI-BS\installer\AI_BS_Studio_Setup.iss` to ensure backend routers (`commercial_gateway`, `routers`) are explicitly included in all future update payload zip files and Inno Setup installer builds.

---

## Verification Plan

### Automated Checks
- Run diagnostic PowerShell comparison script verifying file lengths, timestamps, and SHA256 checksums across all audited files.
- Test updater endpoint query:
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/updater/check"
  ```
  Expected output: `latest_version: "5.199.0"`, `update_available: false`.

### Manual / Integration Verification
- Execute `Update_Desktop_Studio.bat` dry-run or verification pass.
- Verify `Launch_Desktop_Studio.bat` initializes all sub-daemons (Ports 8000, 8080, 8013, 8006, 8005, 5173) without module import errors.
