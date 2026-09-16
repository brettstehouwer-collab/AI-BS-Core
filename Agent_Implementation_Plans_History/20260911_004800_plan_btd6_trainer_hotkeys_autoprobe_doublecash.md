# Implementation Plan: BTD6 Sovereign Memory Trainer Hotkeys, Auto-Probe & Full Pipeline Fix

## 1. Problem Diagnosis & Forensic Isolation

Following live user testing and feedback ("does not apperar to be doing anything at all or workikng properly"):
1. **Zero Global Hotkeys Registered:** Neither Electron (`globalShortcut`) nor Go (`GetAsyncKeyState` / `RegisterHotKey`) was listening for `F1`–`F7`, `F10`. When the user is playing Bloons TD 6 full-screen or windowed, pressing cheat hotkeys had zero effect.
2. **`AddCash` Candidate Gating:** In `main.go`, `AddCash` refused execution with `Cannot add cash: No cash addresses locked` if addresses were not narrowed down to <= 8, failing silently from the user's perspective even when 10 candidates were isolated.
3. **Empty Candidate Fallback Failure in `NextScanCash`:** If `cashCandidates` was empty, `NextScanCash` immediately returned 0 rather than checking existing `cashAddresses` or falling back to `FirstScanCash`.
4. **Missing Lives / Hearts Engine:** `livesAddresses` was defined on a struct but never scanned, probed, or populated anywhere in the daemon.
5. **Double Cash Mode Presets ($1,300):** The user plays with Bloons TD 6 Double Cash mode active (starting cash $1,300 instead of $650). The UI only provided standard presets ($650, $850, $450, $1750), leading to calibration confusion.
6. **No In-Game Auto-Calibration:** The Python trainer had `auto_scan_cash()` and `auto_scan_lives()` that probed standard values in <500ms; the Go daemon lacked this, forcing manual two-step scanning.

---

## 2. Proposed Architectural Changes

### Component 1: Go Native Memory Engine (`go-core/cmd/btd6_trainer_daemon/main.go`)
- **Win32 `GetAsyncKeyState` Polling Routine:**
  - Dedicated 40ms goroutine listening to `VK_F1` (0x70), `VK_NUMPAD1` (0x61), `VK_F2` (0x71), `VK_NUMPAD2` (0x62), `VK_F3` (0x72), `VK_NUMPAD3` (0x63), `VK_F7` (0x76), `VK_NUMPAD7` (0x67), and `VK_F10` (0x79) / `VK_NUMPAD0` (0x60).
  - Uses debouncing so single keypress triggers cleanly once.
  - Automatically triggers auto-probe if memory addresses are not yet established.
- **Auto-Probe Calibration Engine (`AutoScanCash`, `AutoScanLives`):**
  - `AutoScanCash(targetVal)`: Probes starting cash amounts: `[650.0, 1300.0, 850.0, 1700.0, 450.0, 900.0, 1000.0, 2000.0, 200.0, 400.0, 1750.0, 3500.0, 99999.0]`. If matches <= 16, locks them automatically.
  - `AutoScanLives(targetVal)`: Probes starting lives: `[200.0, 150.0, 100.0, 250.0, 1.0, 99999.0]`.
  - Background auto-calibration: Upon initial attach to `BloonsTD6.exe`, automatically runs `AutoScanCash` and `AutoScanLives`.
- **Enhanced `AddCash` and `NextScanCash`:**
  - `AddCash`: If `cashAddresses` has targets, writes to them. If `cashAddresses` is empty but `cashCandidates` has <= 16 targets, locks them and writes immediately. If both are empty, runs `AutoScanCash()` then injects.
  - `NextScanCash`: If `cashCandidates` is empty, checks `cashAddresses`; if both are empty, falls back to `FirstScanCash(newVal)`.
- **Dual-Alignment Support:**
  - Try 8-byte alignment first; if 0 matches, fallback to 4-byte alignment to handle packed IL2CPP structures.
- **Full Lives Tracking:**
  - Implement `FirstScanLives`, `NextScanLives`, `AutoScanLives` with tick freeze loop support.

### Component 2: Electron Main Process (`trainer_frontend/src/main/index.ts`)
- Add global shortcut registration as a secondary fallback.
- Ensure clean child process lifecycle and stdio pipeline.

### Component 3: React UI Renderer (`trainer_frontend/src/renderer/src/App.tsx`)
- Add **`⚡ Auto-Calibrate (Scan All In-Game Values)`** one-click button in Hero banner and Scanner tab.
- Add Double Cash starting presets (`[$1300] Normal x2`, `[$1700] Easy x2`, `[$900] Hard x2`) with visual indicator.
- Add **`🔒 Lock Current Cash`** button directly on the Match Cash calibration card.
- Add **`❤️ Match Lives Calibration`** card with quick presets (`200`, `150`, `100`, `250`, `1`) and `Lock Lives (99,999)`.
- Add step-by-step in-game calibration guidance banner.

### Component 4: Build, Packaging & Verification
- Compile Go binary to all 4 target paths.
- Rebuild Electron unpacked package (`npm run build:unpack`).
- Run automated unit and integration tests.
- Update architectural ledgers, bump version to `v5.250.0`, and update chronologies.

---

## 3. Verification Plan

### Automated Tests
- `python -m pytest tests/test_go_trainer_daemon.py tests/test_game_trainer.py tests/test_e2e_trainer.py -v`

### Manual Verification
- Launch unpacked application via `Launch_BTD6_Electron_Trainer.bat`.
- Verify process detection, auto-calibration probe, hotkeys, and cash/lives locking.
