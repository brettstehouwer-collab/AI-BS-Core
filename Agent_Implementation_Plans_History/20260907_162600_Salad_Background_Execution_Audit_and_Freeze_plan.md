# Forensic Audit Report & Remediation Plan: Salad Background Execution

A complete diagnostic and forensic audit of the Salad installation (`E:\Salad`, `E:\SaladData`, and `C:\Users\footb\AppData\Roaming\Salad`) was conducted to investigate background execution, auto-start mechanisms, and resource utilization.

---

## 1. Executive Summary & Verdict

- **User Suspicion:** Salad has been starting and running in the background for over a month without clicking "Start".
- **Forensic Verdict:** **Confirmed 100% True.** 
  Salad installed a persistent Windows Service (`SaladBowl`) configured with `AUTO_START` under `NT AUTHORITY\SYSTEM`. Every time Windows boots, this service initializes silently in session 0 without opening any UI window.
- **Auto-Start & Scheduling Directives:**
  - `config.json` explicitly schedules automated compute ("Chopping") for **168 out of 168 hours a week (24 hours a day, 7 days a week)**.
  - `config.txt` defines `AutoStartMinutes: 1`, triggering execution after 60 seconds of idle time.
  - `SALAD_AUTO_LAUNCH: true` is enabled.
- **Active Resource & Compute Impact (Current State as of September 7, 2026):**
  - **Live Background Presence:** PIDs `6460` (`Salad.Bootstrapper.exe`) and `10760` (`Salad.Bowl.Service.exe`) are currently active, holding persistent HTTPS sockets to Salad's cloud network and sending heartbeats every 60 seconds (1,400+ heartbeats today).
  - **GPU Compute & Hashrate Consumption:** **Not currently active.** Forensic log analysis reveals that active GPU mining (`T-Rex` and `Rigel`) ran heavily between July 19 and August 15, 2026, bandwidth sharing (`sgs-client`) stopped August 17, and the WSL container was last accessed August 30. Current hourly workload starts fail with DLL signature errors due to an installation path split between `C:\ProgramData` and `E:\SaladData`.

---

## 2. Technical Evidence & Forensic Findings

### A. Active Background Processes & Network Sockets
| Metric | Detail |
| :--- | :--- |
| **Active Service Process** | `PID 6460`: `Salad.Bootstrapper.exe` (Started 2026-09-06 16:47:08) |
| **Child Worker Process** | `PID 10760`: `Salad.Bowl.Service.exe` (Started 2026-09-06 16:47:09) |
| **Execution Context** | `NT AUTHORITY\SYSTEM` (Elevated LocalSystem background service) |
| **Binary Path** | `E:\SaladData\ProgramFiles\Salad\SaladBootstrapper\Salad.Bootstrapper.exe` |
| **Network Endpoints** | Established HTTPS connections to Cloudflare/Salad IPs (`172.67.75.26:443`, `104.26.1.249:443`), local listening sockets on `127.0.0.1:5000` and `127.0.0.1:49686` |
| **Telemetry Activity** | Continuous `Heartbeat` requests every 60 seconds logged in `E:\SaladData\ProgramData\Salad\logs\log-20260907.txt` |

### B. Windows Service Configuration (`SaladBowl`)
```text
SERVICE_NAME: SaladBowl
DISPLAY_NAME: Salad Bowl
TYPE               : 10  WIN32_OWN_PROCESS
START_TYPE         : 2   AUTO_START
ERROR_CONTROL      : 1   NORMAL
BINARY_PATH_NAME   : "C:\Program Files\Salad\SaladBootstrapper\Salad.Bootstrapper.exe" --sb "C:\Program Files\Salad\SaladBowl\Salad.Bowl.Service.exe"
SERVICE_START_NAME : LocalSystem
```

### C. Persistent Configuration Files
1. `C:\Users\footb\AppData\Roaming\Salad\config.json`:
   - `"SALAD_AUTO_LAUNCH": "true"`
   - `"SALAD_AUTO_STOP_ENABLED": "true"`
   - `"SALAD_SCHEDULED_CHOPPING_WEEK"`: Configured with `"AutoStart"` across all 7 days (Monday through Sunday), for all 24 hours per day (168 blocks).
   - `"SALAD_CHOPPING_INDEFINITELY_PAUSED": "false"`
   - `"SALAD_IS_MINING_WORKLOAD_ENABLED": "true"`
2. `E:\SaladData\ProgramData\Salad\config.txt`:
   - `"AutoStartMinutes": "1"`
   - `"ElevatedWslMemoryMb": "32900"` (Pre-allocates up to 32 GB of system RAM for WSL containers).

### D. Historical Workload Timelines (From 319 Log Files)
- **T-Rex Miner (NVIDIA Mining Workload):** 55 log files. Heavily active from **July 19, 2026 to July 24, 2026**.
- **Rigel Miner (NVIDIA Multi-Algorithm):** 84 log files. Active from **July 21, 2026 to August 15, 2026**.
- **Bandwidth Sharing (SGS Client Residential Proxy):** 118 log files across 8 regional routing nodes. Active from **July 19, 2026 to August 17, 2026**.
- **WSL Container Disk Image (`ext4.vhdx`):** 698 MB disk image in `E:\SaladData\ProgramData\Salad\wsl\ext4.vhdx`. Last modified **August 30, 2026 at 13:43:22**.
- **Recent Behavior (August 31 – September 7, 2026):** Service sends hourly requests to start `systeminformation` and `ndm`, but execution aborts with DLL verification errors. No GPU mining or network container execution has occurred during this window.

---

## 3. Actionable Remediation Options

Please review the following three remediation paths. In accordance with system safety rules, no commands will be executed until you confirm your preferred option.

### Option 1: Immediate Disablement & Service Freeze (Recommended if preserving files)
- **Action:**
  1. Immediately stop the `SaladBowl` Windows service (`sc stop SaladBowl`).
  2. Terminate running processes `Salad.Bootstrapper.exe` (PID 6460) and `Salad.Bowl.Service.exe` (PID 10760).
  3. Reconfigure `SaladBowl` service startup type to `Disabled` (`sc config SaladBowl start= disabled`).
  4. Modify `%APPDATA%\Salad\config.json` to disable `SALAD_AUTO_LAUNCH` and clear `SALAD_SCHEDULED_CHOPPING_WEEK`.
- **Result:** Salad can never auto-start on boot or idle. Files remain intact on `E:\` if you ever wish to inspect or reopen the client manually.

### Option 2: Complete Clean Uninstallation & File Purge (Recommended if no longer using Salad)
- **Action:**
  1. Terminate running processes and stop/delete the `SaladBowl` Windows service (`sc delete SaladBowl`).
  2. Unregister the `salad-enterprise-linux` WSL2 distribution (`wsl --unregister salad-enterprise-linux`).
  3. Run silent uninstaller: `E:\Salad\Uninstall Salad.exe /S`.
  4. Remove remaining cache, container disks, and logs in `E:\SaladData` and `%APPDATA%\Salad`.
- **Result:** Complete removal of all binaries, services, WSL virtual disks, and background hooks from the system.

### Option 3: Passive Configuration Override Only
- **Action:**
  1. Leave binaries and service installed, but configure service to `Manual` start (`sc config SaladBowl start= demand`).
  2. Toggle `SALAD_AUTO_LAUNCH: false` and set `AutoStartMinutes: 0`.
- **Result:** The service only starts if you manually launch the Salad UI application.

---

## 4. Verification Plan

Upon selection and confirmation of an option:
1. **Process Inspection:** Verify via `Get-Process` and `psutil` that zero Salad/Kale processes are running.
2. **Service Verification:** Run `sc qc SaladBowl` to confirm service is stopped and disabled or deleted.
3. **Network Audit:** Verify ports `5000` and `49686` are closed and outbound connections to `172.67.75.26` are terminated.
