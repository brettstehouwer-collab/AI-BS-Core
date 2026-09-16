# Diagnosis & Implementation Plan: Getting the BTD6 Game Trainer to Work

## 1. Problem Diagnosis & Root Causes

During inspection of `game_trainer/` and testing against active game sessions, several critical failure modes were identified:

### 1.1 Unaligned Memory Matches (False Positives)
- In `game_trainer/core/memory.py`, `scan_exact_value` executes `data.find(packed_val)` across all committed memory pages.
- In 64-bit Unity IL2CPP games (`BloonsTD6.exe`), heap objects allocated in C# align primitive fields (such as 64-bit `double` for cash or 32-bit `int` for monkey money) to natural 4-byte or 8-byte boundaries (`address % 4 == 0` or `address % 8 == 0`).
- The current scanner matches byte patterns at unaligned offsets (e.g. `0x18de8408443` where `address % 8 == 3`). Modifying or freezing these unaligned offsets corrupts unrelated buffers or strings without altering actual in-game simulation values.

### 1.2 The 25ms Infinite Scanning CPU Loop
- In `game_trainer/profiles/btd6_profile.py`, `_tick_cash()` and `_tick_lives()` call `self.auto_scan_cash()` whenever `self.cash_addresses` is empty.
- Because `_tick_loop()` in `trainer.py` executes every 25ms (`poll_rate_ms=25`), when the game is at a menu, loading, or when starting cash differs from hardcoded presets (`[650.0, 850.0, ...]`), `auto_scan_cash()` triggers full 2.7GB memory scans continuously 40 times per second.
- This saturates CPU cores, starves the Tkinter GUI message pump, and blocks hotkey interception.

### 1.3 Missing "Next Scan" (Filtering Scan) Workflow
- BTD6 allocates simulation entities dynamically upon match start. Multiple addresses may coincidentally hold the starting value (e.g. `650.0`).
- While `MemoryManager.filter_scan()` exists in `memory.py`, it was not exposed or integrated into `BTD6Trainer`, the CLI launcher, the transparent HUD overlay, or the web dashboard.
- The standard, reliable mechanism for locating dynamic memory values is:
  1. **First Scan:** Search for initial cash (e.g., $650). Yields candidates.
  2. **In-game Delta:** Spend money (buy a tower) or pop balloons (e.g., cash becomes $450 or $675).
  3. **Next Scan (Filter):** Scan candidate addresses for the updated number. This filters hundreds of candidates down to 1-2 exact addresses in <1 millisecond.
  4. **Lock & Freeze:** Writing or locking the filtered address modifies the live in-game cash immediately.

### 1.4 Incomplete HUD Overlay Scanner Tab
- The `Scanner` tab in `game_trainer/core/overlay.py` only included an entry field for Monkey Money.
- It completely lacked inputs for Match Cash scanning, candidates counter, and "Next Scan / Filter" actions.

### 1.5 Scanner Buffer Churn & Boundary Gaps
- `read_bytes()` instantiates a new 2MB `ctypes.create_string_buffer` on every read call, generating high garbage collection pressure over 1,500+ iterations per scan.
- Sequential 2MB chunk reads do not overlap, causing target values straddling chunk boundaries to be skipped.

---

## 2. Proposed Technical Changes

### 2.1 Core Memory Engine Optimizations (`game_trainer/core/memory.py`)
- **Pre-allocated Reusable Buffer:** Add an internal reusable ctypes string buffer to `MemoryManager` (`self._scan_buffer = ctypes.create_string_buffer(2 * 1024 * 1024 + 16)`) to eliminate repeated memory allocation during scans.
- **Chunk Boundary Overlap:** Overlap chunk reads by `len(packed_val) - 1` bytes so values spanning 2MB page borders are captured.
- **Natural Boundary Alignment Filter:** Add an `alignment: int = 4` parameter to `scan_exact_value` so unaligned false matches (`address % alignment != 0`) are discarded immediately.

### 2.2 Profile Refactoring (`game_trainer/profiles/btd6_profile.py`)
- **Decouple Ticks from Scanning:** Remove `self.auto_scan_cash()` and `self.auto_scan_lives()` from `_tick_cash()` and `_tick_lives()`. The tick loop must only write to already-locked addresses.
- **Multi-Stage Candidate Tracking:**
  - Add `cash_candidates: List[int]`.
  - Add `first_scan_cash(target_cash: float) -> int`: Scans memory for aligned doubles, populates `cash_candidates`, and returns match count.
  - Add `next_scan_cash(new_cash: float) -> int`: Runs `filter_scan` on `cash_candidates`. If candidate count <= 4, automatically commits them to `cash_addresses` and activates the freeze loop.
  - Update `_trigger_prepare`: Runs candidate detection and provides explicit feedback on whether addresses were locked.

### 2.3 Transparent HUD Overlay Upgrades (`game_trainer/core/overlay.py`)
- **Expanded Scanner Tab:**
  - Add "Current Match Cash" input field.
  - Add `[First Scan]` button.
  - Add `[Next Scan / Filter]` button.
  - Add Candidates count display (`Matches: 0` -> `Matches: 18` -> `Locked: 2`).
  - Add quick buttons for standard starting values: `[$650 (Easy/Med)]`, `[$850 (Deflation)]`, `[$450 (Chim/Hard)]`.
- **Live Status Feed:** Display locked address count in real time on the HUD.

### 2.4 CLI Launcher Enhancements (`game_trainer/launch_btd6_trainer.py`)
- Add CLI commands:
  - `scan <val>`: Initiates First Scan.
  - `next <val>`: Executes Next Scan filter on existing candidates.
  - `lock <addr>`: Manually locks an address if desired.

### 2.5 Backend & Frontend Dashboard Alignment
- **Backend Router (`backend/routers/memory_lab_router.py`):**
  - Add `POST /api/memory-lab/filter-cash`: Accepts `{ current_cash: float }`, invokes `next_scan_cash()`, and returns remaining candidates and lock status.
- **Dashboard UI (`frontend/src/components/ProcessMemoryLabTab.jsx`):**
  - Add "Next Scan" action button and candidates indicator badge next to the Cash input box.

---

## 3. Verification Plan

### Automated Tests
- Run `python tests/test_game_trainer.py` to verify:
  - Alignment filtering in `scan_exact_value`.
  - Chunk overlap verification.
  - `first_scan` and `next_scan` narrowing on sandbox memory.
- Run `python tests/test_e2e_trainer.py` to verify end-to-end sandbox execution.

### Live Game Verification (Bloons TD 6)
1. Launch `BloonsTD6.exe` and enter a single-player map.
2. Launch trainer (`Launch_BTD6_Trainer.bat` or web dashboard).
3. In the Scanner tab or CLI, enter initial cash (e.g. `650`) and click **First Scan**.
4. Place any tower (e.g. Dart Monkey) so cash changes (e.g. to `435`).
5. Enter `435` and click **Next Scan**.
6. Verify candidate count drops to 1-2 addresses and status changes to `LOCKED`.
7. Toggle `F1` (Unlimited Match Cash) or click preset pills (`$50k`, `$99.9k`) and verify cash updates immediately in-game.

---

## 4. User Review & Confirmation

Review the proposed diagnosis and architectural changes above. Execution will begin upon your explicit confirmation.
