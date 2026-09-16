# Implementation Plan: Native Pearl (PRL) & sCash Direct Mining & Clore Renter Disengagement (v5.197.0)

## Problem & Context
The user observed their machine running under maximum hardware load (88% CPU, 86% RAM, 100% GPU / 445W). Investigation revealed that an active Clore.ai renter container (`clore-order-2094183`) was dual-mining:
1. `peakminer` saturating the NVIDIA GeForce RTX 4090 with Pearl (PRL) matrix-multiplication hashing (`pearlhash`).
2. `xmrigMiner` saturating 19 cores (1898% CPU) of the AMD Ryzen 9 9950X with sCash RandomX hashing (`rx/scash`).

The user requested an explanation of Pearl Coin and PeakMiner, how to mine directly without renting through third parties, and subsequently chose to immediately disengage the renter container to free hardware while they obtain their `prl1...` address.

## Proposed Changes

### Hardware Reclamation & Renter Disengagement
- Disengaged `clore-hosting.service` via `systemctl stop clore-hosting.service`.
- Stopped Docker containers `clore-order-2094183` and `clore-proxy-2094183-uEiqZ8sH-v4`.
- Verified power and thermals: RTX 4090 dropped from 445W/64°C to 66W/35°C, CPU dropped to 0% idle compute.

### Binary Extraction & Preservation
- Extracted Linux `peakminer` binary into `/root/peakminer_backup/` and `C:\AI-BS\miners\peakminer_linux\`.
- Extracted Linux `xmrigMiner` and `xmrigDaemon` binaries into `C:\AI-BS\miners\xmrig_scash\`.

### Sovereign Mining Launchers
- Created `C:\AI-BS\miners\Mine_Pearl.bat` for 1-click Windows execution against `us.pearl.herominers.com:1200`.
- Created `C:\AI-BS\miners\mine_pearl.sh` for native WSL2 execution with power limiting (`--gpu-power 400`).
- Created `C:\AI-BS\miners\Stop_Clore_Rental.bat` for 1-click container and service shutdown.
- Created `C:\AI-BS\miners\Mine_sCash_CPU.bat` for CPU mining on Ryzen 9 9950X.

### Architectural Ledgers & Version Parity
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` with entry for `v5.197.0`.
- Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` with version bump `5.197.0` and persist artifact copy to `saved_data/artifacts/20260907_AI_BS_Master_Ecosystem_Manual_v5.197.0.md`.
- Update frontend version badges across 23 files to `v5.197.0`.
- Rebuild frontend with `npm run build` and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
- Archive `task.md` and `implementation_plan.md` to chronological archives.

## Verification Plan
1. `nvidia-smi` check verifying idle power (66W) and temperature (35°C).
2. WSL process table check verifying absence of miner processes.
3. Verification that `C:\AI-BS\miners\` scripts exist and have correct permissions.
4. Validation of production frontend build and live Firebase hosting deployment.
