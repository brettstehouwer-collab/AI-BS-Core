# Task List: Comprehensive Phone & Tablet Repair Guide Subsystem

- [x] **Phase 1: Knowledge Database & Backend Architecture** <!-- id: 0 -->
  - [x] Design SQLite schema in `database/aibs_phone_repair.db` for repair guides, device specifications, diagnostic troubleshooting decision trees, part grades, and repair ticket logs <!-- id: 1 -->
  - [x] Build `backend/core/phone_repair_knowledge.py` with comprehensive, structured repair data for:
    - iPhone (Screens, Batteries, Ports, Face ID serialization, Board Micro-soldering)
    - iPad (Digitizers, Laminated Displays, Charge Ports, Bent Housing)
    - Android Phones (Samsung, Pixel, Motorola - Curved AMOLEDs, Fingerprint Calibration, Odin Flashing)
    - Android Tablets (Galaxy Tab, Lenovo, Amazon Fire - Charge Ports, Batteries, Digitizers) <!-- id: 2 -->
  - [x] Create `backend/routers/phone_repair_router.py` mounted at `/api/repair` with endpoints for guides, diagnostic decision trees, checklists, search, and custom repair ticket persistence <!-- id: 3 -->

- [x] **Phase 2: Frontend Phone & Tablet Repair Subsystem Component** <!-- id: 4 -->
  - [x] Build `frontend/src/components/PhoneRepairGuideTab.jsx` with rich, state-of-the-art UI:
    - Categorized Device Navigator (Apple iPhone, Apple iPad, Android Phone, Android Tablet)
    - Interactive Step-by-Step Teardown & Repair Walkthroughs with Safety & Temperature specs
    - Interactive Diagnostic Troubleshooting Decision Trees (No Power, No Display, Boot Loop, Charging Issues)
    - Repair Cost & Profit Margin Calculator (Parts Grade: OEM vs Soft OLED vs Hard OLED vs Incell)
    - Post-Repair Quality Assurance Diagnostic Checklist <!-- id: 5 -->
  - [x] Synchronize component to `frontend/components/PhoneRepairGuideTab.jsx` <!-- id: 6 -->

- [x] **Phase 3: Ecosystem Wiring & Tab Navigation** <!-- id: 7 -->
  - [x] Register `phone_repair` in `frontend/App.jsx` tab registry, Sidebar, and TopNavbar <!-- id: 8 -->
  - [x] Connect repair actions to the AI-BS Episodic Memory Vault (`personal_memory.record_ecosystem_event`) <!-- id: 9 -->

- [x] **Phase 4: Verification, Master Ledger Update & Production Deployment** <!-- id: 10 -->
  - [x] Test backend API routes and guide queries <!-- id: 11 -->
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (bump to `v5.161.0`) <!-- id: 12 -->
  - [x] Build production bundle (`npm run build`) and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 13 -->
