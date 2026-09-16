# Implementation Plan: Permanent Clore.ai Hosting Stability & WSL2 Always-On Persistence

Address the 0.46% reliability rating and recurring offline drops on Clore.ai by eliminating WSL2 idle shutdowns, configuring guest power event handling, isolating the GPU host from Vast.ai restarts, and maintaining a persistent Windows background keepalive.

## User Review Required

> [!IMPORTANT]
> **Vast.ai Service Deactivation:** Vast.ai services (`vastai.service`, `vast_metrics.service`, `vastai_bouncer.service`, and the aggressive `/etc/cron.d/vastai_restart_everything` cron restart loop) will be disabled inside WSL2 to dedicate the single NVIDIA RTX 4090 to Clore.ai without port, container, or driver collisions.
>
> **Shutdown Script Decoupling:** Line 33 of `Shutdown_AI_BS.bat` (`systemctl stop clore-hosting.service`) will be removed so that stopping local AI-BS desktop studio processes does not terminate the Clore hosting agent or kill active customer rental workloads.

## Proposed Changes

### Host Configuration (`C:\Users\footb\.wslconfig`)

#### [MODIFY] [C:\Users\footb\.wslconfig](file:///C:/Users/footb/.wslconfig)
- Under section `[wsl2]`, add `vmIdleTimeout=-1` to prevent Windows 11 Hyper-V from tearing down the WSL2 virtual machine when no interactive console is attached.

---

### WSL2 Guest Power & Logind Configuration

#### [NEW] `/etc/systemd/logind.conf.d/ignore-poweroff.conf`
- Deploy systemd-logind drop-in configuration:
  ```ini
  [Login]
  HandlePowerKey=ignore
  HandleSuspendKey=ignore
  HandleHibernateKey=ignore
  ```
- Reload and restart `systemd-logind` to ignore ACPI power signals from Windows.

---

### Vast.ai Service & Cron Remediation

#### [MODIFY] WSL2 Services & Crontab
- Stop and disable `vastai.service`, `vast_metrics.service`, `vastai_bouncer.service`, and `vast_metrics.timer`.
- Disable `/etc/cron.d/vastai_restart_everything` (rename to `.disabled` or comment out) so the 60-second restart loop ceases disrupting Docker.
- Comment out user crontab entries in `root` that invoke Vast scripts (`update_scripts.sh`, `send_mach_info.py`, `enable_vms.py`).

---

### Ecosystem Script Updates (`C:\AI-BS`)

#### [MODIFY] [C:\AI-BS\Shutdown_AI_BS.bat](file:///C:/AI-BS/Shutdown_AI_BS.bat)
- Excise line 33 (`wsl.exe -d Ubuntu -u root -- systemctl stop clore-hosting.service >nul 2>&1`). Clore hosting must remain sovereign and active during local studio cleans.

#### [MODIFY] [C:\AI-BS\Start_Clore_Server.bat](file:///C:/AI-BS/Start_Clore_Server.bat)
- Update launcher to ensure a hidden persistent keepalive (`wsl.exe -d Ubuntu -u root -- sleep infinity`) is verified/spawned, guaranteeing WSL2 process tree persistence on Windows.

#### [NEW] [C:\AI-BS\scripts\ensure_clore_keepalive.ps1](file:///C:/AI-BS/scripts/ensure_clore_keepalive.ps1)
- Create PowerShell daemon script to check and ensure the WSL keepalive process is active, registering an optional scheduled task at Windows logon (`AI-BS-Clore-WSL-Keepalive`) if desired.

---

### Documentation & Ledgers

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Log architectural entry detailing WSL2 idle timeout bypass, systemd-logind ACPI signal suppression, Vast.ai collision resolution, and persistent keepalive architecture.

#### [MODIFY] [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Document Clore.ai hosting persistence procedures and WSL2 keepalive operations.

## Verification Plan

### Automated & Diagnostic Tests
1. **WSL Idle Persistence:**
   - Verify `vmIdleTimeout=-1` in `.wslconfig`.
   - Verify `systemd-logind` active with `ignore-poweroff.conf`.
   - Test background process persistence: launch background sleep, close sessions, and verify WSL uptime exceeds 5 minutes without resetting `docker ps` container uptimes.
2. **Vast.ai Isolation:**
   - Verify `systemctl is-active vastai` returns `inactive`.
   - Verify `/etc/cron.d/vastai_restart_everything` is disabled.
3. **Clore Hosting Live State:**
   - Verify `clore-hosting.service` remains `active (running)`.
   - Verify active rental container `clore-order-2094183` uptime continues increasing without interruption.
   - Verify RTX 4090 compute state via `nvidia-smi`.
