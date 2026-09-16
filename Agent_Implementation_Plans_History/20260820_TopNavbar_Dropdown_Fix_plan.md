# Implementation Plan: Fix TopNavbar Dropdown Menu Interface Layering & Clipping Bug

Resolve the issue where top navbar hub dropdown menus (`Stehouwer Publishing ▼`, `Hollywood Creation Suite ▼`, `Noto Hospitality OS ▼`, etc.) are hidden behind interface modules when hovering over them.

## Proposed Changes

### Top Navigation & Dropdown Styling
- Implement fixed-position floating dropdown positioning (`position: 'fixed'`) for hub dropdown menus in `TopNavbar.jsx`.
- Compute dynamic `getBoundingClientRect()` top and left coordinates on `onMouseEnter` / `onClick` of each hub group button.
- Elevate dropdown `zIndex` to `99999` to ensure top-layer rendering above all interface panels, modals, canvases, and `SubTabBar`.
- Add scroll listener on `scrollRibbonRef` to cleanly dismiss open dropdown menus during horizontal panning.
- Update top navbar version badge to `v5.38.1 (Phase 47.1)`.

### Core Integration & System Ledgers
- Update version to `v5.38.1 (Phase 47.1)` across `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
- Persist `saved_data/artifacts/20260820_AI_BS_Master_Ecosystem_Manual.md`.
- Update `artifact_history.md` and sync master chronologies.

## Verification Plan
1. Run `npm run build` from `C:\AI-BS\frontend`.
2. Run `firebase deploy --only hosting --non-interactive`.
