# Task: BTD6 Memory Trainer Diagnosis & Operational Fixes

- [*] Diagnose why numbers are not changing in active BloonsTD6.exe session <!-- id: 0 -->
  - [*] Identify unaligned memory false positives (`addr % 8 != 0`) in `scan_exact_value`
  - [*] Identify 25ms tick loop CPU saturation caused by repetitive `auto_scan_cash` calls
  - [*] Identify missing Next Scan / Filter Scan workflow in profile and HUD overlay
  - [*] Identify missing cash calibration inputs in HUD overlay Scanner tab
- [*] Optimize memory scanner in `game_trainer/core/memory.py` <!-- id: 1 -->
  - [*] Add single pre-allocated reusable scan buffer to eliminate GC allocations
  - [*] Implement chunk boundary overlap (`val_len - 1`) to prevent missing values on 2MB borders
  - [*] Enforce memory alignment (`alignment=4` or `8`) for primitive type scans
- [*] Upgrade `BTD6Trainer` in `game_trainer/profiles/btd6_profile.py` <!-- id: 2 -->
  - [*] Remove 25ms repetitive scan from `_tick_cash` and `_tick_lives`
  - [*] Implement multi-stage scanning: `first_scan_cash(val)`, `next_scan_cash(val)`, and candidate tracking
  - [*] Update `_trigger_prepare` with actual candidate feedback and status reporting
- [*] Upgrade HUD Overlay in `game_trainer/core/overlay.py` <!-- id: 3 -->
  - [*] Add Cash First Scan & Next Scan input controls and match counters to Scanner tab
  - [*] Add Live Address & Candidate Counter feedback labels
- [*] Update CLI Launcher in `game_trainer/launch_btd6_trainer.py` <!-- id: 4 -->
  - [*] Add `next` command for sub-millisecond filtering
  - [*] Improve in-game guidance for single-player / sandbox mode
- [*] Update Backend Router and Web UI Mirrors <!-- id: 5 -->
  - [*] Add `/filter-cash` endpoint to `backend/routers/memory_lab_router.py`
  - [*] Update `ProcessMemoryLabTab.jsx` with Next Scan button and candidate count
- [*] Run test suite (`tests/test_game_trainer.py`, `tests/test_e2e_trainer.py`) <!-- id: 6 -->
- [*] Version bump, frontend build, Firebase deployment, and ledger sync <!-- id: 7 -->


