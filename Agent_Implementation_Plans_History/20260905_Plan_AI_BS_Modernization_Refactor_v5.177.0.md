# Implementation Plan: Sovereign Bible Hub & New Testament Markdown Library

## Overview
The user requested:
1. Generation of three specific master Markdown files in `C:\AI-BS`:
   - `C:\AI-BS\Mark.md` (16 Chapters)
   - `C:\AI-BS\Luke.md` (24 Chapters)
   - `C:\AI-BS\John.md` (21 Chapters)
2. A complete Bible page inside AI-BS with the 27 New Testament books categorized across:
   - The Gospels (4 Books, 89 Chapters)
   - Church History (1 Book: Acts, 28 Chapters)
   - Paul’s Epistles (13 Books, 100 Chapters)
   - General Letters (8 Books, 34 Chapters)
   - Prophecy / Apocalyptic (1 Book: Revelation, 22 Chapters)
   - Summary telemetry: 66 Total Books, 1,189 Total Chapters (929 OT, 260 NT), ~31,102 Verses.

---

## User Review Required
> [!IMPORTANT]
> - All texts use the public domain King James Version (KJV), completely 100% free with zero cloud dependencies or paid APIs.
> - The new Bible page will be directly integrated into the AI-BS tab matrix (`BibleStudyTab.jsx`) and linked to Stehouwer LLM / BS-Chat for chapter study and theological reasoning.
> - Frontend will be built and deployed live to `https://ai-bs-dashboard.web.app` in accordance with our strict deployment rules.

---

## Proposed Changes

### 1. New Testament Markdown Generation
- Generate `C:\AI-BS\Mark.md` (16 Chapters, ~80 KB) in the exact format of `Matthew.md`.
- Generate `C:\AI-BS\Luke.md` (24 Chapters, ~140 KB) in the exact format of `Matthew.md`.
- Generate `C:\AI-BS\John.md` (21 Chapters, ~110 KB) in the exact format of `Matthew.md`.
- Generate the full 27 New Testament books catalog in `C:\AI-BS\Documents\Bible\New_Testament\` and compile `C:\AI-BS\Documents\King_James_New_Testament.md`.

### 2. Frontend Bible Hub Page
#### [NEW] [BibleStudyTab.jsx](file:///C:/AI-BS/frontend/src/components/BibleStudyTab.jsx) & mirror `frontend/components/BibleStudyTab.jsx`
- Sleek dark mode aesthetics with gold and royal navy accents, clean verse typography, and responsive grid layouts.
- Header Statistics Banner: 66 Books, 1,189 Chapters (929 OT, 260 NT), ~31,102 Verses.
- 5 Category Cards:
  - 🕊️ The Gospels (Matthew, Mark, Luke, John)
  - 🏛️ Church History (Acts)
  - 📜 Paul's Letters (Romans through Philemon)
  - ✉️ General Letters (Hebrews through Jude)
  - ⚡ Prophecy / Apocalyptic (Revelation)
- Interactive Bible Chapter Reader with verse numbers, copy verse, chapter quick-jump, and full-text search.
- Direct "Send to BS-Chat / Stehouwer LLM" action to study or analyze any chapter.

### 3. Application Integration & Version Parity
#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Register `bible_hub` tab in the `tabs` array.
- Bump version badges to `v5.176.0`.
- Update `TopNavbar.jsx` and `PhoneRepairGuideTab.jsx` version badges.

### 4. Ledgers & Deployment
- Rebuild frontend bundle (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, and history archives.

---

## Verification Plan
1. Verify `Mark.md`, `Luke.md`, and `John.md` exist on `C:\AI-BS\` with correct line and chapter counts.
2. Verify `BibleStudyTab.jsx` loads in the frontend, allows book and chapter navigation, and renders verses with high fidelity.
3. Test searching verses (e.g. "John 3:16", "grace", "faith").
4. Run `npm run build` and `firebase deploy` to verify live hosting at `https://ai-bs-dashboard.web.app`.
