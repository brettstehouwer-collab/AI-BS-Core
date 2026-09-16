# Tasks: Permanent Clore.ai Hosting Stability & WSL2 Always-On Persistence

- [x] Step 1: Prevent WSL from Shutting Down on Idle <!-- id: 0 -->
  - [x] Add `vmIdleTimeout=-1` to `C:\Users\footb\.wslconfig` under `[wsl2]` <!-- id: 1 -->
- [x] Step 2: Prevent `systemd-logind` from Powering Off on ACPI Signals <!-- id: 2 -->
  - [x] Create `/etc/systemd/logind.conf.d/ignore-poweroff.conf` inside WSL2 Ubuntu <!-- id: 3 -->
  - [x] Restart `systemd-logind` in WSL2 <!-- id: 4 -->
- [x] Step 3: Deactivate Vast.ai Services & Disruptive Cron Loops <!-- id: 5 -->
  - [x] Stop and disable `vastai.service`, `vast_metrics.service`, `vastai_bouncer.service`, and `vast_metrics.timer` <!-- id: 6 -->
  - [x] Disable `/etc/cron.d/vastai_restart_everything` and Vast-related root crontab lines <!-- id: 7 -->
- [x] Step 4: Decouple Clore from Shutdown Scripts & Implement Background Keepalive <!-- id: 8 -->
  - [x] Remove line 33 (`systemctl stop clore-hosting.service`) from `C:\AI-BS\Shutdown_AI_BS.bat` <!-- id: 9 -->
  - [x] Update `C:\AI-BS\Start_Clore_Server.bat` to verify/spawn hidden background keepalive (`sleep infinity`) <!-- id: 10 -->
  - [x] Create `C:\AI-BS\scripts\ensure_clore_keepalive.ps1` for background watchdog persistence <!-- id: 11 -->
  - [x] Launch persistent background keepalive process now <!-- id: 12 -->
- [x] Step 5: Verification & Ledger Maintenance <!-- id: 13 -->
  - [x] Verify `docker ps` and `clore-hosting.service` retain uninterrupted uptime <!-- id: 14 -->
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` <!-- id: 15 -->
  - [x] Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, bump version, and persist artifact <!-- id: 16 -->
