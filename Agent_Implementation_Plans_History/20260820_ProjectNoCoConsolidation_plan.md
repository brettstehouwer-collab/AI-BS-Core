# Implementation Plan: Consolidate "Theatrical Stage & Prompter" and "Project NoCo" into One Unified Tab (v5.42.0)

Merge the separate `Theatrical Stage & Prompter` module (`NoCoVisionTab.jsx`) into `ProjectNoCoStudioTab.jsx` as a dedicated **`🎤 Live Stage Switcher & Teleprompter`** sub-deck, removing tab redundancy from the top navigation bar.

## Proposed Changes
1. Import `<TheatricalStageSwitch />` and `<TheatricalMicClient />` into `ProjectNoCoStudioTab.jsx` and add `stage_prompter` sub-tab.
2. Remove standalone `noco_vision` entry from `navigationConfig.js` masterHubs under `Hollywood Creation Suite`.
3. Route `noco_vision` key to `ProjectNoCoStudioTab` in `App.jsx`.
4. Bump version to `v5.42.0 (Phase 51)` across code, ledgers, manuals, and chronologies.
5. Rebuild Vite frontend and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
