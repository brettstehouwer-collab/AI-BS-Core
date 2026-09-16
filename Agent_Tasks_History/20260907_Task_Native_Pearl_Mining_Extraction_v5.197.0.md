# Task: Native Pearl (PRL) & sCash Direct Mining Extraction & Renter Disengagement (v5.197.0)

## Objectives
- [x] Investigate saturated hardware (100% GPU / 445W and 1898% CPU) and identify renter workloads (`peakminer` on RTX 4090 and `xmrigDaemon`/`xmrigMiner` on Ryzen 9 9950X in `clore-order-2094183`)
- [x] Safeguard and extract local miner binaries:
  - [x] Back up `peakminer` Linux binary to `/root/peakminer_backup/` and Windows `C:\AI-BS\miners\peakminer_linux\`
  - [x] Back up `xmrigDaemon` and `xmrigMiner` CPU binaries to `C:\AI-BS\miners\xmrig_scash\`
- [x] Provide user with architectural analysis of Pearl (PRL) PoUW matrix multiplication consensus, HeroMiners pool mining vs solo full-node mining, and sCash RandomX CPU mining
- [x] Disengage renter container and suppress auto-respawn:
  - [x] Stop `clore-hosting.service` in WSL2
  - [x] Gracefully stop containers `clore-order-2094183` and `clore-proxy-2094183-uEiqZ8sH-v4`
  - [x] Verify hardware drops to idle (RTX 4090 cooled from 64°C/445W to 35°C/66W, Ryzen 9 9950X dropped from 1898% CPU to idle)
- [x] Create 1-click launchers for sovereign mining:
  - [x] `C:\AI-BS\miners\Mine_Pearl.bat` (Windows batch script invoking WSL2 `peakminer` on RTX 4090 with `--gpu-power 400`)
  - [x] `C:\AI-BS\miners\mine_pearl.sh` (WSL2 bash script)
  - [x] `C:\AI-BS\miners\Stop_Clore_Rental.bat` (1-click script to stop Clore service and rental containers)
  - [x] `C:\AI-BS\miners\Mine_sCash_CPU.bat` (1-click CPU miner for sCash on Ryzen 9 9950X)
- [x] Update documentation, master ledgers, and frontend version parity to v5.197.0:
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`
  - [x] Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` and persist versioned artifact
  - [x] Sweep frontend version badges to `v5.197.0`
  - [x] Build and deploy frontend to Firebase Hosting (`ai-bs-dashboard.web.app`)
  - [x] Archive task and implementation plan to historical chronologies
