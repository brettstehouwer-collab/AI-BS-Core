# Implementation Plan: Comprehensive Phone & Tablet Repair Subsystem

Build and integrate a dedicated, full-stack **Phone & Tablet Repair Guide & Diagnostics Subsystem** in AI-BS, providing deep, step-by-step master technical guides, diagnostic decision trees, micro-soldering schematics references, and a parts/profit calculator categorized across **Apple iPhones**, **Apple iPads**, **Android Phones (Samsung, Pixel, Motorola)**, and **Android Tablets**.

---

## Architectural Breakdown

```
                    ┌────────────────────────────────────────────────────────┐
                    │      Phone & Tablet Repair Subsystem (UI Tab)          │
                    │   (frontend/src/components/PhoneRepairGuideTab.jsx)    │
                    └───────────────────────────┬────────────────────────────┘
                                                │
          ┌─────────────────────────────────────┼─────────────────────────────────────┐
          ▼                                     ▼                                     ▼
┌──────────────────┐                  ┌──────────────────┐                  ┌──────────────────┐
│ Categorized      │                  │ Interactive      │                  │ Hardware         │
│ Repair Guides    │                  │ Diagnostic Trees │                  │ Calculator & QA  │
│ • Apple iPhone   │                  │ • DC Power Bench │                  │ • OEM vs OLED    │
│ • Apple iPad     │                  │ • Backlight Rail │                  │ • Profit Margins │
│ • Android Phone  │                  │ • Tristar Shorts │                  │ • 18-Point QA    │
│ • Android Tablet │                  │ • Boot Loops     │                  │   Checklist      │
└─────────┬────────┘                  └─────────┬────────┘                  └─────────┬────────┘
          │                                     │                                     │
          └─────────────────────────────────────┼─────────────────────────────────────┘
                                                │
                                                ▼
                    ┌────────────────────────────────────────────────────────┐
                    │         FastAPI Repair Router (/api/repair)            │
                    │      (backend/routers/phone_repair_router.py)          │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                    ┌────────────────────────────────────────────────────────┐
                    │        SQLite Database & Episodic Memory Vault         │
                    │       (database/aibs_phone_repair.db & FTS5)           │
                    └────────────────────────────────────────────────────────┘
```

---

## User Review Required

> [!IMPORTANT]
> - **100% Free & Local:** All database records, hardware pinout reference charts, step-by-step procedures, and diagnostic trees run offline from NVMe SQLite without requiring internet access or paid software.
> - **Complete Professional Depth:** Covers everything from basic screen & battery swaps to advanced Face ID serialization (JCID/QianLi), TrueTone copy, ultrasonic fingerprint calibration (*#0*# service menu), iPad digitizer separation, laser back-glass housing swaps, and board-level DC power supply current draw analysis (0.00A, 0.05A, 0.20A, VDD_MAIN shorts).

---

## Proposed Changes

### 1. Database & Core Repair Knowledge (`database/aibs_phone_repair.db` & `backend/core/phone_repair_knowledge.py`)
- Tables:
  - `repair_guides`: Detailed markdown guides, safety specs (heat mat temperature, battery discharge voltage), required screwdrivers (Pentalobe P2/P5, Tri-Point Y000, Torx T3/T4/T5, Phillips PH000), difficulty score, estimated repair time.
  - `diagnostic_trees`: Symptom -> Probe Point -> Measurement -> Root Cause -> Fix Action.
  - `part_grades`: Quality comparisons (OEM Pull, Refurb, Soft OLED, Hard OLED, Incell LCD) with price ranges and failure risks.
  - `repair_tickets`: Local tracking for customer repairs (device, serial/IMEI, symptom, parts used, cost, price, warranty).

### 2. Categorized Repair Guides Included:
1. **Apple iPhone:**
   - Screen Replacement & TrueTone / EEPROM Copy (iPhone 8 through 16 Pro Max).
   - Battery Replacement & Battery Health BMS Tag-on Flex re-programming.
   - Charge Port (Lightning / USB-C) Dock Flex & Taptic Engine.
   - Camera & LiDAR Module Replacement (with anti-reflection precautions).
   - Back Glass Replacement (Cold Chamber vs Laser Etch vs Complete Housing Swap).
   - Face ID & Flood Illuminator / Dot Projector micro-soldering.
   - Logic Board Micro-Soldering (VDD_MAIN short detection, thermal camera, NAND reball, Tristar/Hydra USB IC).
2. **Apple iPad (Standard, Mini, Air, Pro):**
   - Air-Gap Digitizer vs LCD separation (iPad 9th/10th Gen vs Pro laminated screens).
   - Adhesive softening (90°C heat mat + Isopropyl alcohol 99% pull technique).
   - Charge Port Micro-Soldering (soldering 36-pin USB-C / Lightning dock flex to motherboard).
   - Bent Aluminum Housing Straightening and Corner Bevel filing.
3. **Android Phones (Samsung Galaxy, Google Pixel, Motorola, OnePlus):**
   - Curved AMOLED & Frame Assembly Replacement.
   - Under-Display Optical & Ultrasonic Fingerprint Calibration (`*#0*#` test mode & Google Pixel repair tool).
   - Sub-board / Daughterboard Charge Port & Mic Replacement.
   - Back Cover De-Gluing & Waterproof Gasket Sealing (B-7000 / Pre-cut tape).
   - Thermal Paste & Graphite Vapor Chamber Heat Spreading.
   - Software Flashing, Unbricking & FRP Bypass (Odin 3.14.4 / Fastboot / EDL 9008 mode).
4. **Android Tablets (Samsung Tab, Lenovo, Amazon Fire):**
   - Glass Digitizer Separation with Diamond Wire / Heat.
   - Battery Removal from plastic chassis without cell puncture.
   - Micro-USB / USB-C Port Board Replacement & Jumper Wire Repair.

### 3. Backend REST API Router (`backend/routers/phone_repair_router.py`)
- `GET /api/repair/categories`: Lists Apple, Android, iPad, Tablet categories.
- `GET /api/repair/guides`: Filter guides by category, device, or repair type.
- `GET /api/repair/guide/{guide_id}`: Full step-by-step repair walkthrough.
- `GET /api/repair/diagnostics`: Interactive troubleshooting decision trees.
- `POST /api/repair/tickets/create`: Save customer repair ticket to SQLite.
- `GET /api/repair/tickets`: List customer repair history.

### 4. Frontend UI Module (`PhoneRepairGuideTab.jsx`)
- Sleek modern layout with:
  - **Category Tabs:** 🍏 Apple iPhone | 📱 Apple iPad | 🤖 Android Phones | 📟 Android Tablets
  - **Interactive Teardown Stepper:** Step-by-step instructions with tool requirements, temperature indicators (🔥 75°C - 80°C), screw organizers (color-coded magnetic screw mats), and pro technician warnings.
  - **Hardware Diagnostic Tree:** Click symptoms (e.g., *"Phone pulls 0.05A and freezes"*) to navigate to immediate multimeter probe points (PP_VDD_MAIN / PMIC).
  - **Repair Quote & Profit Calculator:** Interactive part grade selector (Incell, Hard OLED, Soft OLED, OEM) with labor rate calculation.
  - **Post-Repair 18-Point QA Checklist:** Interactive verification checklist for Touch, Face ID/Fingerprint, Proximity Sensor, TrueTone, Microphones, Qi Wireless, and Thermal equilibrium.

---

## Verification Plan

### Automated Tests
1. Python unit tests verifying SQLite database creation and guide indexing.
2. Test REST API endpoints (`GET /api/repair/categories`, `GET /api/repair/guides`, `GET /api/repair/diagnostics`).
3. Verify Vite bundle compilation (`npm run build`).

### Manual Verification
1. Navigate to the new **🔧 Phone & Tablet Repair** tab in AI-BS.
2. Switch between Apple iPhone, iPad, Android Phone, and Android Tablet categories.
3. Open a step-by-step repair guide (e.g. iPhone Screen & TrueTone serialization, Samsung Curved AMOLED).
4. Test the Interactive Diagnostic Tree for "No Power / 0.00A Current Draw".
5. Run parts cost & profit calculator and create a test repair ticket.
6. Verify live deployment on `https://ai-bs-dashboard.web.app`.
