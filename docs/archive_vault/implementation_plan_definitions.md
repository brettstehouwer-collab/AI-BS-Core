# Definitions Module & Interactive History Implementation Plan

To replace your hardcoded "Back Story & Lore" tab with a live, interactive timeline, I will construct a new architecture that dynamically reads and parses your physical `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` file! 

## User Review Required

> [!IMPORTANT]
> **Data Collection Tab Plan**: Before we begin this Definitions module, I need to know if you still want me to execute the **Data Collection Hub** plan from earlier? We can do the Data Collection Hub first, and then I can build this Definitions dictionary right after! Let me know which order you prefer.

## Proposed Changes for Definitions Module

---

### Backend API Expansion

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Create a new endpoint: `GET /api/v1/dictionary/ledger-history`.
- This endpoint will open `C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, parse every single `## Development Entry`, extract the Timestamp, Rationale, and Technical Specs, and serve it to the frontend as clean JSON.

---

### Frontend UI & Organization

#### [NEW] [DefinitionsModuleTab.jsx](file:///C:/AI-BS/frontend/components/DefinitionsModuleTab.jsx)
- Build a new master hub component for the "Definitions & Dictionary".
- Create sub-navigation inside this hub (e.g., "Glossary", "Evolution History").

#### [MODIFY] [BullshitEvolutionHistory.jsx](file:///C:/AI-BS/frontend/components/BullshitEvolutionHistory.jsx)
- Remove the hardcoded 5-phase array.
- Wire it up to fetch the live ledger data from the new `/api/v1/dictionary/ledger-history` endpoint.
- Rebuild the UI into a clickable accordion timeline. When you click on a milestone (e.g. `v8.17.0 OAuth Integration`), it gracefully expands downward to reveal the full Rationale and Technical Specs you documented for that build.

#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Unregister the standalone "Lore" tab and properly nest it inside the new "Definitions Module" in your sidebar/top nav.

## Verification Plan
1. Parse the local Markdown ledger safely in Python without corrupting file locks.
2. Verify the React accordion smoothly handles the dynamic height of massive ledger entries.
3. Perform the background `npm run build && firebase deploy` sequence so the dictionary pushes live.
