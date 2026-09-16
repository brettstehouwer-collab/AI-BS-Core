# Transparent HUD Overlay & Function Keys Architecture

Design and implementation of a transparent on-screen HUD overlay and Function Key (F1-F12) dual-binding across the standalone game trainer and the AI-BS web dashboard.
<!-- id: 0 -->
## Status: Completed
- [x] Specification and implementation plan <!-- id: 1 -->
- [x] Upgrade `hotkeys.py` and `trainer.py` with multi-key / dual-binding support (F-keys + Numpad) <!-- id: 2 -->
- [x] Create standalone native Win32 transparent click-through HUD overlay (`game_trainer/core/overlay.py`) <!-- id: 3 -->
- [x] Update `btd6_profile.py` with F1-F6 and F10 quick keys <!-- id: 4 -->
- [x] Update standalone CLI launcher `launch_btd6_trainer.py` and `Launch_BTD6_Trainer.bat` to launch HUD <!-- id: 5 -->
- [x] Add Function Key badges and floating transparent HUD overlay to `ProcessMemoryLabTab.jsx` <!-- id: 6 -->
- [x] Rebuild frontend bundle (`npm run build`) and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 7 -->
- [x] Update Master Architectural Ledger & Ecosystem Manual to `v5.244.0` <!-- id: 8 -->
