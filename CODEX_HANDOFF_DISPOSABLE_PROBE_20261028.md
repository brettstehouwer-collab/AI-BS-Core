# CODEX HANDOFF: Disposable Windows 11 VM Isolation & Sealing Pipeline
**Date**: October 28, 2026  
**Target Subsystem**: Isolated Worker Control / `windows_vm` Execution Backend (Record 174 / ADR-110)  
**Handoff Author**: Antigravity Pair-Programmer  
**Recipient**: OpenAI Codex  

---

## 1. Executive Summary & Verified Machine State

All active background tasks have been **halted and killed**. No locks or active processes remain.

| Target Component | State | Exact Identification / Path |
| :--- | :--- | :--- |
| **Disposable Probe VM** | `poweroff` | Name: `AI-BS-DisposableProbe-20261026`<br>UUID: `e5a2fe34-7b90-460c-83af-903d51b4bb16`<br>Path: `E:\AI-BS-DisposableProbe-v1\AI-BS-DisposableProbe-20261026\AI-BS-DisposableProbe-20261026.vbox` |
| **System Virtual Disk** | Base clean | `E:\AI-BS-DisposableProbe-v1\system.vdi` (64 GB allocated, Windows 11 Enterprise Eval Build 26100) |
| **Preserved Integration Base** | `poweroff` / Locked | Name: `AI-BS-Eval-Base-20261023`<br>UUID: `6c5a53da-ab80-4ecb-8be6-4059266f736e`<br>Status: Preserved and strictly excluded from disposable execution. |
| **Guest Credentials** | Active | User: `aibs_vm_worker` (`S-1-5-21-980229162-2331381249-3281308904-1001`)<br>Password: `h/9WVEX1fDbz++Q0wlaJ5YvU5KyGCUtbqgS6+UXgaA1!`<br>Setup User: `aibs_bootstrap` (Disabled)<br>Credential File: `C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1\credentials\guest.txt` |
| **Worker Control Root** | Ready | `C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1\` |
| **Repository State** | Active Work | `C:\AI-BS` HEAD: `e45f1b5075619bd3ae7f4bbb506c0ea021eb6732`.<br>138 tracked modified files preserved in place (uncommitted). |
| **Cloudflare Rolled Token** | Updated | `CLOUDFLARE_API_TOKEN=cfut_d9avNIMX3ZksBxjWpuxHAl0MBRSIederstkXajFc3efce103` in `C:\AI-BS\.env`. |

---

## 2. Root Cause Analysis & Fix of Path/Timestamp Divergence

During image sealing (`Seal-WorkerImage.ps1`), two subtle platform divergence bugs were diagnosed and solved in `DisposableProbe.psm1`:

1. **POSIX vs Windows Path Slashes (`OUTSIDE_DISPOSABLE_STORAGE`)**:
   - VirtualBox 7.x writes snapshot differencing disk locations into `.vbox` XML with forward slashes: `Snapshots/{uuid}.vdi`.
   - `Assert-StorageLocation` had `[IO.Path]::GetFullPath($Path) -ceq $Path`, which failed on any mixed-slash string.
   - **Fix Applied**: `Assert-StorageLocation` and `Parse-MediumInfo` now canonicalize slashes via `[IO.Path]::GetFullPath` and `$value.Replace('/', '\')`, strictly asserting that the canonical root remains under `E:\AI-BS-DisposableProbe-v1\`.

2. **In-Memory COM vs On-Disk XML Divergence (`SNAPSHOT_CHANGED_AFTER_BOOTSTRAP`)**:
   - When `Readback-And-SnapshotWorker.ps1` ran `FinalInspect` immediately after `snapshot take`, the VirtualBox COM daemon reported sub-millisecond precision on `VMStateChangeTime` (`.926000000`).
   - However, VirtualBox’s on-disk XML format truncates sub-seconds (`2026-10-28T16:46:45Z`). When `Inspect-SealedWorker.ps1` later inspected the machine, `VMStateChangeTime` returned `.000000000`, causing `config_sha256` to diverge from `terminal_config_sha256`.
   - **Fix Applied**: In `DisposableProbe.psm1`, `Parse-VMInfo` now normalizes `VMStateChangeTime` fractional seconds to `.000000000` and normalizes SATA/CfgFile paths to Windows backslashes.

---

## 3. Resumption Instructions for Codex

Codex can complete the sealing and enrollment workflow in 4 deterministic steps:

### Step 1: Run Fresh Bootstrap & Snapshot Capture
Ensure the VM is powered off and run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\footb\.gemini\antigravity\brain\07218072-c562-45e3-944e-be2a9f2e06e9\scratch\run_bootstrap_prep.ps1'
```
*Expected Result*: State transitions to `SNAPSHOT_PROPOSED_AWAITING_CONTROLLER_SEAL` with exit code 0.

### Step 2: Execute Sealer to Publish Signed Profile
Immediately run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\footb\.gemini\antigravity\brain\07218072-c562-45e3-944e-be2a9f2e06e9\scratch\run_seal_auto.ps1'
```
*Expected Result*: `Seal-WorkerImage.ps1` locks the storage ACLs, streams the base hash, signs `policy\profile.json`, and outputs `PROVISIONED`.

### Step 3: Populate Enrollment & Run Non-Mutating Verification
1. Create `C:\AI-BS\saved_data\vm_runner_config\vbox_guest_config.json`:
```json
{
  "vm_uuid": "e5a2fe34-7b90-460c-83af-903d51b4bb16",
  "snapshot_name": "AIBS_ACCEPTED_DIAGNOSTIC_V1",
  "username": "aibs_vm_worker",
  "guest_python": "C:\\Users\\aibs_vm_worker\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
  "enrolled": true
}
```
2. Verify backend resolution:
```powershell
python C:\AI-BS\scripts\verify_and_connect_guest_runner.py status
```
*Confirm*: `windows_vm` transitions to `READY`.

3. Run canary execution and automated test suites:
```powershell
python C:\AI-BS\scripts\verify_and_connect_guest_runner.py verify-vbox
python C:\AI-BS\scripts\verify_and_connect_guest_runner.py test-all
```

### Step 4: Synchronize & Deploy via Release Orchestrator
```powershell
python "C:\Users\footb\.gemini\config\skills\aibs-release-orchestrator\scripts\release_orchestrator.py" sync
python "C:\Users\footb\.gemini\config\skills\aibs-release-orchestrator\scripts\release_orchestrator.py" build
python "C:\Users\footb\.gemini\config\skills\aibs-release-orchestrator\scripts\release_orchestrator.py" deploy
```
