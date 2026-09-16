# Implementation Plan: Vast.ai Machine 150272 Marketplace Listing & Self-Test Verification

## Overview
Machine 150272 (AMD Ryzen 9 9950X, 1x NVIDIA RTX 4090 24GB, 52GB DDR5, 860GB NVMe, 855/371 Mbps) is registered and active on Vast.ai under team account `AI-BS`. The `bad bandwidthtest2` error has been completely resolved via a custom NVIDIA Container Toolkit (CDI) wrapper in `Ubuntu-24.04`. The remaining phase is listing the machine for rental and executing the automated self-test to achieve verified status.

---

## Technical Audit & Root Cause Analysis

### Resolved Issue: `bad bandwidthtest2`
- **Error:** `bad bandwidthtest2: {'ERROR_CONDITION': 'not r_H2D or not r_D2H or not r_D2D', 'gpu_idx': 0}`
- **Root Cause:** WSL2's native `nvidia-container-toolkit` generated a legacy CDI specification (`cdiVersion: 0.3.0`) exposing only device `name: all`. When Vast's `kaalia_docker_shim` launched `vastai/test:bandwidth-test-nvidia` with `--env NVIDIA_VISIBLE_DEVICES=0`, containerd failed with `unresolvable CDI devices ... /gpu=0`.
- **Patch Applied:** Installed `/usr/bin/nvidia-ctk` wrapper in `Ubuntu-24.04` that intercepts `cdi generate`, updates `cdiVersion` to `0.5.0`, and clones the device specification under discrete device name `'0'`.
- **Validation:** Tested container execution directly and as user `vastai_kaalia`:
  ```json
  {"gpu_idx": 0, "bw_cpu_dev": 12.6, "bw_dev_cpu": 12.5, "bw_dev_ram": 82.8}
  ```
  Kaalia uploaded the successful benchmark to Vast controllers (`32.197.45.244:7070`). On the Vast.ai server, `error_description` is now `null`, `gpu_mem_bw` is `141.5`, and `pcie_bw` is `12.7`.

---

## Operational Plan

### Step 1: List Machine 150272 for Rental
Vast.ai self-test requires an active rentable offer on the machine. Unlisted machines fail preflight checks (`Rentable offer available actual: 0 offers required: >= 1 offers`).
- Target pricing:
  - On-demand GPU price (`-g`): **$0.44 / hr**
  - Minimum spot bid floor (`-b`): **$0.34 / hr**
  - Storage price (`-s`): **$0.10 / GB / month**
  - Bandwidth egress (`-u`): **$0.01 / GB**
  - Bandwidth ingress (`-d`): **$0.01 / GB**
- Command:
  ```bash
  wsl.exe -d Ubuntu-24.04 -u root vastai list machine 150272 -g 0.44 -b 0.34 -s 0.10 -u 0.01 -d 0.01 --url https://console.vast.ai
  ```

### Step 2: Temporary Mining Pause & Self-Test Execution
During self-test, Vast.ai downloads a benchmark container (PyTorch) and runs compute benchmarks (DLPerf). To ensure maximum benchmark performance and prevent CUDA OOM/thermal contention:
1. Temporarily pause `peakminer` in `Ubuntu` distro (`kill -STOP 982544`).
2. Run self-test:
   ```bash
   wsl.exe -d Ubuntu-24.04 -u root vastai self-test machine 150272 --url https://console.vast.ai
   ```
3. Once self-test completes and the machine reaches verified status (`verification: "verified"`), resume `peakminer` immediately (`kill -CONT 982544`).

### Step 3: Concurrency Watchdog Daemon
Ensure `miners/pearl_payout_watcher.py` or a dedicated background watcher checks `docker ps` in `Ubuntu-24.04`:
- When a Vast container enters `Up` status, automatically pause `peakminer` (`kill -STOP`).
- When the container exits or terminates, automatically resume `peakminer` (`kill -CONT`).

---

## Verification Plan
- Verify machine 150272 shows `listed: true` in `vastai show machines`.
- Confirm `vastai self-test` produces a passing DLPerf score.
- Confirm web dashboard shows `Verified` status and the machine is searchable.
