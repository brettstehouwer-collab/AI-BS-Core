# Task: BTD6 Sovereign Memory Trainer - Hotkeys, Auto-Probe & Full Pipeline Fix

## Status: COMPLETED
- [x] Forensic diagnosis of reported non-responsiveness (missing global hotkeys, AddCash locked address gating, missing lives scanner, Double Cash presets) <!-- id: 1 -->
- [x] Upgrade Go Native Memory Engine (`go-core/cmd/btd6_trainer_daemon/main.go`): <!-- id: 2 -->
  - [x] Add Win32 `GetAsyncKeyState` background polling goroutine for F1–F7, F10 hotkeys during active gameplay
  - [x] Implement `AutoScanCash` probing standard and Double Cash starting sums ([650, 1300, 850, 1700, 450, 900, 1000, 2000, 200, 400, 1750, 3500])
  - [x] Implement `AutoScanLives`, `FirstScanLives`, `NextScanLives` for health auto-locking ([200, 150, 100, 250, 1])
  - [x] Enhance `AddCash` to write to candidates (<=16) and auto-probe if empty
  - [x] Enhance `NextScanCash` to fallback to cashAddresses or FirstScan when candidates empty
  - [x] Add dual-alignment fallback (8-byte then 4-byte) for IL2CPP doubles
- [x] Upgrade Electron Main Process (`trainer_frontend/src/main/index.ts`): <!-- id: 3 -->
  - [x] Register globalShortcut fallback hooks for F1-F7, F10
- [x] Upgrade React UI Renderer (`trainer_frontend/src/renderer/src/App.tsx`): <!-- id: 4 -->
  - [x] Add "⚡ Auto-Calibrate (Scan All In-Game Values)" one-click button
  - [x] Add Double Cash starting presets ($1300, $1700, $900) and direct "🔒 Lock Current Cash" button
  - [x] Add "❤️ Match Lives Calibration" card with presets and instant GodMode freeze
  - [x] Add step-by-step in-game calibration guidance banner
- [x] Compile & Multi-Target Deployment: <!-- id: 5 -->
  - [x] Compile Go binary to `go-core`, `EXE`, `trainer_frontend/resources`, and unpacked distribution
  - [x] Rebuild Electron unpacked package (`npm run build:unpack`)
- [x] Automated Test Suite Verification: <!-- id: 6 -->
  - [x] Update and run `test_go_trainer_daemon.py`, `test_game_trainer.py`, `test_e2e_trainer.py` (13/13 passed)
- [x] Ledger & Ecosystem Manual Synchronization: <!-- id: 7 -->
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`
  - [x] Bump version to `v5.250.0` in `AI_BS_MASTER_ECOSYSTEM_MANUAL.md` and persist artifact
  - [x] Update chronologies (`MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, `MASTER_HISTORICAL_INDEX.md`)
  - [x] Sync UI version badges to `v5.250.0`
