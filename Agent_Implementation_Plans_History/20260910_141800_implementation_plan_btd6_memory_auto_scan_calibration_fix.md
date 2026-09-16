# Implementation Plan: BTD6 Memory Auto-Scan, Multi-Address Locking & Value Calibration

## 1. Problem Diagnosis & Root Cause
During live testing with Bloons TD 6 running at PID `26496` (`E:\SteamLibrary\steamapps\common\BloonsTD6\BloonsTD6.exe`), the trainer attached successfully to `BloonsTD6.exe` and resolved `GameAssembly.dll` (`0x7ff8df1a0000`). However, cheats failed to affect the game for the following reasons:
1. **Uninitialized Address:** `BTD6Trainer` initialized `cash_address = 0` and `lives_address = 0`. Without providing a manual `--cash-addr 0x...` argument, the trainer held an address of `0x0`.
2. **Silent No-Op on Hotkeys:** When `F1` or `NUMPAD 1` was pressed, `_tick_cash()` checked `if self.cash_address:`, which evaluated to `False`, silently doing nothing.
3. **No Automatic In-Game Memory Calibration:** Unity IL2CPP dynamically allocates match simulation entities on the heap. BTD6 does not use static memory offsets across game updates. A dynamic committed-memory value scanner is required to lock live match cash and Monkey Money.
4. **Empirical Proof of Write:** We scanned the live `BloonsTD6.exe` process for starting cash `650.0` in 2.42s and located exact addresses `0x18de8408443` and `0x18f983dd2e3`. Writing `999,999.0` into both addresses succeeded and was verified in memory.

---

## 2. Technical Architecture & Proposed Changes

### 2.1 Core Memory Engine (`game_trainer/core/memory.py`)
- **`scan_exact_value(value, value_type='double') -> List[int]`:**
  - Scans all committed `PAGE_READWRITE` regions in 2MB chunks using `struct.pack`.
  - Completes full 2.7GB scan across `BloonsTD6.exe` in ~2.4 seconds.
  - Supports `double`, `float`, `int32`, `uint32`, `int64`.
- **`filter_scan(candidate_addresses, new_value, value_type='double') -> List[int]`:**
  - Re-reads only previous matches to filter down to the true address in <1ms after in-game values change.

### 2.2 BTD6 Cheat Profile (`game_trainer/profiles/btd6_profile.py`)
- **Multi-Address Locking:**
  - Replace single `cash_address` with `cash_addresses: List[int]`. BTD6 maintains both an active simulation entity and a UI display mirror; writing to all matched addresses ensures visual and gameplay synchronization.
- **Auto-Scan & Calibration Method:**
  - `auto_scan_cash(target_cash=None)`:
    - If `target_cash` is provided, scans directly.
    - If `None`, probes common starting amounts: `[999999.0, 650.0, 850.0, 450.0, 1000.0, 200.0, 1750.0]`.
    - Automatically locks found addresses to `self.cash_addresses`.
  - `auto_scan_lives(target_lives=None)`:
    - Probes standard starting life counts: `[200.0, 150.0, 100.0, 250.0, 1.0]`.
  - `auto_scan_coins(current_coins)`:
    - Scans for `int32` Monkey Money value on demand.
- **Self-Healing Callbacks:**
  - In `_tick_cash()` and `_trigger_add_cash()`, if `cash_addresses` is empty, automatically triggers `auto_scan_cash()` before execution.
- **New Feature: Quick Monkey Money (Coins):**
  - Add feature `F7`: "Add 50,000 Monkey Money (Coins)".

### 2.3 Standalone CLI Launcher (`game_trainer/launch_btd6_trainer.py`)
- Automatically runs `trainer.auto_scan_cash()` immediately upon attaching to `BloonsTD6.exe`.
- Adds interactive terminal commands:
  - `scan <value>`: Scans and locks cash immediately (e.g. `scan 650` or `scan 1250`).
  - `next <value>`: Re-filters matches after cash changes in-game.
  - `add <amount>`: Instantly adds cash (e.g. `add 50000`).
  - `coins <amount>`: Scans/adds Monkey Money.
  - `lives <amount>`: Scans/locks lives.

### 2.4 AI-BS Web Backend Router (`backend/routers/memory_lab_router.py`)
- Mount `POST /api/memory-lab/scan-cash`: Accepts `{ current_cash?: float }`, runs memory scan on attached process, locks addresses, and returns matched offsets.
- Mount `POST /api/memory-lab/set-cash`: Sets custom cash value across all locked addresses.
- Mount `POST /api/memory-lab/scan-coins`: Scans for Monkey Money as `int32`.

### 2.5 Web Dashboard UI (`frontend/src/components/ProcessMemoryLabTab.jsx`)
- Render an **"In-Game Cash & Coins Auto-Lock"** toolbar at the top of the Gaming Trainer Deck.
- Includes an input field for current displayed cash (`650` default) and a **"Scan & Lock In-Game Cash"** button.
- Shows real-time lock status (e.g. `Locked at 0x18de8408443, 0x18f983dd2e3 ($999,999.00)`).
- Once locked, toggling `Unlimited Match Cash` (`F1`) or clicking `Add $50,000` immediately works.

---

## 3. Verification Plan

### Automated Tests
- Run `python tests/test_game_trainer.py` to verify all 7 unit tests pass.
- Add `test_08_scan_exact_value` to verify `scan_exact_value` and `filter_scan` on self-process heap data.

### Live Process Verification
- Verify against live `BloonsTD6.exe` (PID `26496`):
  - Run `auto_scan_cash()` and verify both addresses lock in <3 seconds.
  - Test freeze loop and value add (`+50,000`).
  - Verify on-screen transparent HUD reflects active status.

### Frontend & Deployment Verification
- Rebuild production bundle via `npm run build`.
- Deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
