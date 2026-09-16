# Tasks: Convert Standalone Desktop App to Dedicated BS-Studio

- [ ] 1. Desktop UI & Component Streamlining <!-- id: 1 -->
  - [ ] Update `BroadcastStudioApp/src/App.jsx` branding header to `BS-STUDIO` <!-- id: 1.1 -->
  - [ ] Restrict `STUDIO_TABS` to Broadcast Studio and Music DAW <!-- id: 1.2 -->
  - [ ] Restrict `MULTI_PRESETS` to Dual (Broadcast + DAW) and Stacked (Broadcast Top / DAW Bottom) <!-- id: 1.3 -->
  - [ ] Remove unused tab imports and dead layout conditional blocks from `App.jsx` <!-- id: 1.4 -->
- [ ] 2. Standalone Compilation & Packaging <!-- id: 2 -->
  - [ ] Run `npm run build` in `BroadcastStudioApp` <!-- id: 2.1 -->
  - [ ] Package standalone electron distribution in `BroadcastStudioApp` <!-- id: 2.2 -->
  - [ ] Mirror updated `app.asar` and runtime binaries to `E:\AI-BS Broadcast Studio\` <!-- id: 2.3 -->
- [ ] 3. Ledger & Manual Synchronization <!-- id: 3 -->
  - [ ] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` (v5.148.0) <!-- id: 3.1 -->
  - [ ] Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (v5.148.0) and copy to `saved_data/artifacts/` <!-- id: 3.2 -->
  - [ ] Log entry in `NotebookLM_Records/artifact_history.md` and `MASTER_HISTORICAL_INDEX.md` <!-- id: 3.3 -->
  - [ ] Archive task list and implementation plan to historical archives <!-- id: 3.4 -->
