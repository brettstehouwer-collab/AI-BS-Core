# Task List: BTD6 Memory Auto-Scan, Value Calibration & Live Injection Fix

<!-- id: 0 -->
## Status: Completed
- [x] Root Cause Analysis of BTD6 trainer non-responsiveness (Completed: verified PID 26496, discovered uninitialized 0x0 cash address, verified live memory writes at 0x18de8408443 and 0x18f983dd2e3) <!-- id: 1 -->
- [x] Implement fast committed RAM value scanner (`scan_exact_value` and `filter_scan`) in `game_trainer/core/memory.py` <!-- id: 2 -->
- [x] Upgrade `btd6_profile.py` with dynamic `auto_scan_cash()`, `auto_scan_lives()`, and `auto_scan_coins()` with multi-address locking <!-- id: 3 -->
- [x] Update `launch_btd6_trainer.py` to auto-calibrate on startup and add interactive `scan <cash>`, `coins <amount>`, and `add <amount>` commands <!-- id: 4 -->
- [x] Add `/api/memory-lab/scan-cash`, `/api/memory-lab/set-cash`, and `/api/memory-lab/scan-coins` endpoints to `backend/routers/memory_lab_router.py` <!-- id: 5 -->
- [x] Add 1-Click "Scan & Lock In-Game Cash / Coins" calibration card and Monkey Money Card 7 to `ProcessMemoryLabTab.jsx` on the web dashboard <!-- id: 6 -->
- [x] Verify unit tests in `tests/test_game_trainer.py` (8/8 passed in 0.058s) and live memory write to running game <!-- id: 7 -->
- [x] Rebuild frontend bundle (`npm run build`) and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 8 -->
- [x] Update Master Architectural Ledger & Ecosystem Manual to `v5.245.0` <!-- id: 9 -->
