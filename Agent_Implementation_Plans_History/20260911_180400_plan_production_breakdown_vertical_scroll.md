# Implementation Plan: Production Breakdown Modal Vertical Wheel Scroll Repair (v5.258.0)

Remediates the vertical wheel scroll failure in the **Production Breakdown & Budget** modal and **Stage Play Breakdown** modal where users cannot scroll up or down to inspect the full stripboard shooting schedule, scene strips, DOOD matrix, or budget.

---

## User Review & Proceed Option

> [!IMPORTANT]
> **Root Cause Identified:**
> Neither `ProductionBreakdownModal.jsx` nor `StagePlayBreakdownModal.jsx` imported their accompanying `.css` stylesheets (`ProductionBreakdownModal.css`, `StagePlayBreakdownModal.css`). As a result:
> 1. The modal rendered unstyled and unconstrained in standard document flow instead of an isolated viewport-bounded overlay (`position: fixed; inset: 0; height: 90vh`).
> 2. The `.tab-content` container lacked flex child scroll boundaries (`min-height: 0; overflow-y: auto`), causing the stripboard content to extend 5,000+ pixels off the bottom of the screen while the parent document suppressed mouse wheel scrolling.
>
> Click the **'Proceed'** button in the artifact header or type confirmation in chat to authorize execution and live deployment.

---

## Proposed Changes

### Component 1: Stylesheet Imports in Breakdown Modals

Both breakdown modal components must explicitly import their required CSS files so Vite bundles the stylesheet rules into the build.

#### [MODIFY] [`frontend/src/components/ProductionBreakdownModal.jsx`](file:///c:/AI-BS/frontend/src/components/ProductionBreakdownModal.jsx)
- Add `import './ProductionBreakdownModal.css';` at line 2.
- Replicate across all 3 mirror paths:
  - `frontend/src/components/components/ProductionBreakdownModal.jsx`
  - `frontend/components/ProductionBreakdownModal.jsx`
  - `frontend/components/components/ProductionBreakdownModal.jsx`

#### [MODIFY] [`frontend/src/components/StagePlayBreakdownModal.jsx`](file:///c:/AI-BS/frontend/src/components/StagePlayBreakdownModal.jsx)
- Add `import './ProductionBreakdownModal.css';` and `import './StagePlayBreakdownModal.css';` at lines 2-3.
- Replicate across all 3 mirror paths:
  - `frontend/src/components/components/StagePlayBreakdownModal.jsx`
  - `frontend/components/StagePlayBreakdownModal.jsx`
  - `frontend/components/components/StagePlayBreakdownModal.jsx`

---

### Component 2: Flexbox Overflow & Wheel Scroll Hardening in CSS

In `ProductionBreakdownModal.css`, flex containers must enforce zero minimum dimensions (`min-height: 0; min-width: 0`) so browser layout engines properly activate `overflow-y: auto` scrollbars instead of expanding to fit content.

#### [MODIFY] [`frontend/src/components/ProductionBreakdownModal.css`](file:///c:/AI-BS/frontend/src/components/ProductionBreakdownModal.css)
- **Modal Container:** Set `max-height: 90vh; overflow: hidden; position: relative;`.
- **Content Grid:** Add `min-height: 0;` to `.modal-content-grid`.
- **Sidebar:** Add `min-height: 0; min-width: 320px;` to `.parameters-sidebar`.
- **Visualization Area:** Add `min-height: 0; min-width: 0;` to `.visualization-area`.
- **Tab Content Pane:**
  - Enforce `min-height: 0; overflow-y: auto; overflow-x: auto;`.
  - Add `overscroll-behavior: contain;` and `-webkit-overflow-scrolling: touch;` to capture all wheel and trackpad scroll events directly inside the active sheet.
- **Scrollbars:** Add dedicated high-visibility dark-mode scrollbars (`::-webkit-scrollbar` with `#334155` thumb and `#0f172a` track).
- Replicate identically across all 3 mirror paths:
  - `frontend/src/components/components/ProductionBreakdownModal.css`
  - `frontend/components/ProductionBreakdownModal.css`
  - `frontend/components/components/ProductionBreakdownModal.css`

---

### Component 3: Version Parity, Master Ledgers & Production Deployment

#### [MODIFY] [`version.txt`](file:///c:/AI-BS/version.txt)
- Increment version from `5.257.0` to `5.258.0`.

#### [MODIFY] Frontend Version Manifests & Badges
- Synchronize `5.258.0` across `package.json`, `version.json`, `sw.js`, `App.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, and `ChatTab.jsx`.

#### [MODIFY] Master Ledgers & Manuals
- Update [`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`](file:///c:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md) with `v5.258.0` entry.
- Update [`docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`](file:///c:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md) to `5.258.0`.
- Persist timestamped copy to `saved_data/artifacts/`.
- Update [`MASTER_TASKS_CHRONOLOGY.md`](file:///c:/AI-BS/MASTER_TASKS_CHRONOLOGY.md) and [`MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`](file:///c:/AI-BS/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md).

---

## Verification Plan

### Automated Verification
1. **Compilation & Syntax:** Verify zero JSX or CSS syntax errors.
2. **Vite Production Build:** Run `npm run build` in `frontend/` to ensure clean asset chunking and CSS bundling into the production distribution.
3. **Live Deployment:** Deploy to Firebase Hosting (`ai-bs-dashboard.web.app`) and confirm HTTP 200 on `/version.json`.

### Manual Verification
1. Open the Production Breakdown & Budget modal from the Screenwriting tab.
2. Verify the modal renders as a centered dark-themed overlay with parameters sidebar on the left and visualization area on the right.
3. Scroll the mouse wheel vertically over Day 1, Day 2, and Day 3 to confirm full range vertical scrolling through all shoot days down to Day N.
