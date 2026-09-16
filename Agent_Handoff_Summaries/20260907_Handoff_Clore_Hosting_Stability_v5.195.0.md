# Checkpoint: Sovereign Clore.ai Hosting Stability & GPU Lease Control
**Timestamp:** 2026-09-07T12:35:00-04:00  
**Project:** Sovereign Clore.ai Hosting Stability, WSL2 Persistence & GPU Lease Control  
**Resume Keyword:** `RESUME_CLORE_HOSTING_PHASE1`  
**System Version:** v5.195.0  

---

## Executive Summary

### Completed Work:
1. **WSL2 Hyper-V Idle Tear-Down Elimination:**
   - Added `vmIdleTimeout=-1` to `C:\Users\footb\.wslconfig` under `[wsl2]`.
   - Prevents Windows 11 Hyper-V from harvesting the idle WSL2 virtual machine when interactive terminal sessions close.

2. **Guest ACPI Signal Suppression:**
   - Deployed drop-in configuration `/etc/systemd/logind.conf.d/ignore-poweroff.conf` inside WSL2 Ubuntu:
     ```ini
     [Login]
     HandlePowerKey=ignore
     HandleSuspendKey=ignore
     HandleHibernateKey=ignore
     ```
   - Reloaded and restarted `systemd-logind`. Prevents virtual host ACPI power/sleep signals from terminating guest services.

3. **Vast.ai Resource & Cron Isolation:**
   - Stopped and disabled `vastai.service`, `vast_metrics.service`, `vastai_bouncer.service`, and `vast_metrics.timer`.
   - Disabled `/etc/cron.d/vastai_restart_everything.disabled` and `/etc/cron.d/vastai_kaalia_update.disabled`, stopping the 60-second Docker bouncing loop.
   - Commented out Vast telemetry lines in root crontab. Dedicates the RTX 4090 exclusively to Clore.ai without container or driver conflicts.

4. **Shutdown Script Decoupling & Persistent Keepalive Watchdog:**
   - Excised line 33 (`systemctl stop clore-hosting.service`) from `C:\AI-BS\Shutdown_AI_BS.bat` so local desktop studio cleans never kill active customer rentals.
   - Created PowerShell watchdog daemon `C:\AI-BS\scripts\ensure_clore_keepalive.ps1` to ensure a permanent background session exists.
   - Registered Windows Scheduled Task `\AI-BS-Clore-WSL-Keepalive` to auto-trigger on user logon.

5. **One-Click Hosting Control Utilities:**
   - Updated `C:\AI-BS\Start_Clore_Server.bat` with keepalive auto-spawning and Docker container status reporting.
   - Created `C:\AI-BS\Stop_Clore_Server.bat` for 1-click stopping of `clore-hosting.service`, terminating active order containers, and verifying GPU release via `nvidia-smi`.

6. **Order 2094183 (720h Accident) Cancellation & GPU Release:**
   - Terminated accidental 720-hour rental container `clore-order-2094183` and proxy container.
   - Stopped `clore-hosting.service` to release the lease on the coordinator.
   - Verified GPU hardware release: 0% GPU compute utilization, 46.3W idle power draw, 23.3 GB free VRAM, 23°C.

7. **Production Ecosystem Synchronization & Deployment:**
   - Synchronized system version badges to `v5.195.0` across 23 codebase files.
   - Built frontend production bundle (`npm run build` in 22.18s) and deployed live to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
   - Updated `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.

---

### Current Hardware & Service State:
- **RTX 4090:** 100% idle, ready for local gaming or AI workloads (0% Util, ~46W, 23°C).
- **Clore Hosting Agent:** Offline / Standby.
- **Next Boot:** Running `Start_Clore_Server.bat` will resume marketplace hosting under the new 72-hour max rental cap.

---

*To resume or inspect Clore hosting work at any time, reference `RESUME_CLORE_HOSTING_PHASE1`.*
