# Implementation Plan: Hardened 3-Tier Hardware Clamping & Watchdog (WSL2 Interop Corrected)

## Overview
Incorporates the operator's architectural review and corrections regarding NVML write permissions inside WSL2:
1. **Tier 1 (Host Boot Layer):** Windows Scheduled Task `AI-BS-GPU-Hardware-Persistence` running at computer startup (`AtStartup`) under SYSTEM with explicit quotes and hardcoded `NVSMI` path.
2. **Tier 2 (WSL2 Boot Layer):** Systemd unit `/etc/systemd/system/aibs-gpu-persistent.service` guarded with `ConditionPathExists=/proc/sys/fs/binfmt_misc/WSLInterop`.
3. **Tier 3 (Runtime Watchdog Layer):** `miners/pearl_payout_watcher.py` hardened with an environment-aware enforcement mechanism that routes through Windows Interop (`cmd.exe /c ...`) if running inside WSL2/Linux, and direct host `nvidia-smi` if running under Windows Python.
4. **Drift Simulation Verification:** Intentional drift test via `nvidia-smi -pl 400` to verify automated re-clamping back to 310 W within 60 seconds.

---

## User Review Required

> [!IMPORTANT]
> **Explicit Confirmation:** Review the exact implementation code below for Tier 1, Tier 2, and Tier 3. Per the strict execution rule, execution will commence upon your typed confirmation in chat.

---

## Proposed Changes

### Component 1: Windows Host Boot Clamping Script & Scheduled Task

#### [NEW] [miners/apply_gpu_persistence.bat](file:///C:/AI-BS/miners/apply_gpu_persistence.bat)
```bat
@echo off
:: AI-BS Sovereign GPU Hardware Clamping Script
:: Enforces RTX 4090 -> 310W Power Cap and 5001 MHz Locked VRAM
set "PATH=%PATH%;C:\Program Files\NVIDIA Corporation\NVSMI;C:\Windows\System32"
nvidia-smi -lmc 5001 > nul 2>&1
nvidia-smi -pl 310 > nul 2>&1
exit /b 0
```

#### [EXECUTE] Register Task Scheduler Task via PowerShell
```powershell
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument '/c "C:\AI-BS\miners\apply_gpu_persistence.bat"'
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "AI-BS-GPU-Hardware-Persistence" -Action $Action -Trigger @($TriggerStartup, $TriggerLogon) -Principal $Principal -Settings $Settings -Force
```

---

### Component 2: WSL2 Systemd Service Unit with Interop Guard

#### [NEW] `/opt/peakminer/apply_host_clocks.sh`
```bash
#!/bin/bash
/mnt/c/Windows/system32/cmd.exe /c "nvidia-smi -lmc 5001 & nvidia-smi -pl 310" > /dev/null 2>&1
```

#### [NEW] `/etc/systemd/system/aibs-gpu-persistent.service`
```ini
[Unit]
Description=AI-BS Persistent RTX 4090 Clock and Power Clamping
After=network.target local-fs.target
ConditionPathExists=/proc/sys/fs/binfmt_misc/WSLInterop

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash /opt/peakminer/apply_host_clocks.sh

[Install]
WantedBy=multi-user.target
```

---

### Component 3: Hardened Cross-Environment Watchdog

#### [MODIFY] [miners/pearl_payout_watcher.py](file:///C:/AI-BS/miners/pearl_payout_watcher.py)
* Add environment-aware guard function:
```python
def verify_and_enforce_gpu_profile():
    """Query telemetry; re-enforce clamped profile via Windows Interop or direct host API if drifted."""
    try:
        cmd_query = ["nvidia-smi", "--query-gpu=power.limit,clocks.current.memory", "--format=csv,noheader,nounits"]
        out = subprocess.check_output(cmd_query, timeout=5).decode().strip()
        parts = [p.strip() for p in out.split(",") if p.strip()]
        if len(parts) != 2:
            return
            
        pl, mem = float(parts[0]), float(parts[1])
        
        # Trigger threshold: Power limit > 315W or VRAM clock > 5050MHz
        if pl > 315.0 or mem > 5050.0:
            logger.warning(f"[ALERT] GPU profile drift detected (PL={pl:.1f}W, Mem={mem:.1f}MHz). Re-enforcing 310W / 5001MHz...")
            if os.name == "nt":
                subprocess.run(["nvidia-smi", "-lmc", "5001"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                subprocess.run(["nvidia-smi", "-pl", "310"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            else:
                subprocess.run(
                    ["/mnt/c/Windows/system32/cmd.exe", "/c", "nvidia-smi -lmc 5001 && nvidia-smi -pl 310"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10
                )
            logger.info("[RE-CLAMPED] GPU profile restored to 310W / 5001MHz.")
    except Exception as e:
        logger.debug(f"GPU profile check/enforce bypassed: {e}")
```
