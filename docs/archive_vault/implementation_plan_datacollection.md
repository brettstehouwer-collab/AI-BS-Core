# Data Collection Hub & API Fix Implementation Plan

I have diagnosed the `<!DOCTYPE...` JSON parsing error you encountered! It happened because the deployed frontend lost track of the live backend URL (`ai-bs.brettstehouwer.live`) and tried to ping Firebase for the API, which returned an HTML 404 page instead. **I have already patched this bug in `LostPropertyTab.jsx` so it will work on the next deployment.**

To fulfill your request for a centralized, visually pleasing **Data Collection Tab**, I propose the following architecture:

## User Review Required

> [!IMPORTANT]
> **Component Migration vs Duplication**: Right now, the Web OSINT Sniffer input box and Run button are inside the "Lost Property" tab. 
> Should I **move** that Sniffer UI entirely into the new Data Collection Tab, or should I leave it in Lost Property and just have the *results* save to the Data Collection Tab? (I recommend moving the entire Sniffer UI to the Data Collection Tab so it becomes your dedicated scraping hub).

## Proposed Changes

---

### Backend Data Persistence

#### [MODIFY] [lost_property_scanner.py](file:///C:/AI-BS/backend/core/lost_property_scanner.py)
- Update `run_web_osint_scan()` to not only return the scraped results to the frontend but also **save them as JSON files** to a structured folder: `C:\AI-BS\backend\data\osint_scans\`.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Create a new endpoint `GET /api/v1/data-collection/osint` that reads the `osint_scans` directory and serves all historical data to the frontend so you can review past scans without re-running them.

---

### Frontend UI & Organization

#### [NEW] [DataCollectionTab.jsx](file:///C:/AI-BS/frontend/components/DataCollectionTab.jsx)
- Build a visually pleasing "Data Collection Hub".
- Create an "OSINT Sniffers" sub-section.
- Build a beautiful grid to render the saved historical data that the backend provides.
- (Pending your decision above) Host the input fields to trigger new web scans directly from this tab.

#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Register the new `DataCollectionTab`.
- Group it in the sidebar directly underneath `Stehouwer CMS` and the other Stehouwer Publishing tools for organizational parity.

## Verification Plan
1. I will execute the backend changes and create the new data directories.
2. I will build the `DataCollectionTab.jsx` and hook it into your main App routing.
3. I will run a background deployment (`npm run build && firebase deploy`) so you can instantly see the new tab and verify the bug fix.
