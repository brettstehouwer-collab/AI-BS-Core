# Implementation Plan: Ingest Full NoCo Technical Specs & Support Facilities Deck (v5.43.0)

Ingest all technical specifications from the NoCo drive document bundle (`Noco shiiiit.docx`, `Nocorf1.docx`, `now will you go over each detail...docx`) directly into `ProjectNoCoStudioTab.jsx`, formalizing support facilities, operational scenario load profiles, ag sensor networks, and wastewater infrastructure.

## Proposed Changes
1. Expand `ProjectNoCoStudioTab.jsx` with 3 new interactive sub-decks: Support Facilities (Rehearsal, Recording, Costume/Set Workshop, Barns), Operational Load Profile Calculator (Performance, Rehearsal, Maintenance scenarios), and Ag Sensor Networks / Wastewater Architecture.
2. Bump system version to `v5.43.0 (Phase 52)`.
3. Update master ledgers, manuals, artifact history, and chronologies.
4. Build Vite frontend and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`).
