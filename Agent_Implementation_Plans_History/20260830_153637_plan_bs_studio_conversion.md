# Implementation Plan: Convert Desktop App to Dedicated "BS-Studio" (Broadcast & Music DAW Only)

Streamline the standalone desktop application into a focused, lightweight, and high-performance **"BS-Studio"** containing exclusively the **Broadcast Studio (OBS/NVENC)** and the **Music DAW (Tone.js & VST3)**.

## User Review Required
> [!IMPORTANT]
> - All extraneous tabs (ComfyUI Diffusion, Neural Voice AI, Video Meetings, Screenplay/Teleprompter, Unreal Engine 3D Bridge, Syndication, and Drop Deck) will be removed from the standalone desktop top navigation bar.
> - The standalone desktop header will feature dedicated single-click switches for **Broadcast Studio**, **Music DAW**, and **Dual Split Modes** (Side-by-Side and Top/Bottom Stacked).
> - The full web dashboard (`ai-bs-dashboard.web.app` / `frontend/`) will remain complete and accessible for all other multi-tenant, crypto, and research capabilities.

## Proposed Changes

### 1. Standalone Desktop UI & Layout Streamlining

#### [MODIFY] [App.jsx](file:///c:/AI-BS/BroadcastStudioApp/src/App.jsx)
- Update branding header to **`BS-STUDIO`** with status indicator.
- Refactor `STUDIO_TABS` to include only:
  1. **📻 Broadcast Studio (OBS & NVENC)** (`#00e5ff`)
  2. **🎹 Music DAW & VST3** (`#10b981`)
- Refactor `MULTI_PRESETS` to include only:
  1. **Dual: Broadcast + DAW** (Side-by-Side split)
  2. **Stacked: Broadcast Top / DAW Bottom**
- Clean up unused multi-grid layout branches while preserving the Tone.js audio graph, DSP VST bridge, on-air PiP monitor, soundboard triggers, and Localhost Dev Tools (F12) prober.

---

### 2. Standalone Build & Packaging

#### [EXECUTE] [Build_Broadcast_Studio_Standalone.bat](file:///c:/AI-BS/BroadcastStudioApp/Build_Broadcast_Studio_Standalone.bat)
- Compile Vite production client in `BroadcastStudioApp`.
- Package standalone unpacked distribution and NSIS installer (`dist-electron/win-unpacked/`).
- Mirror updated `app.asar` and runtime binaries to `E:\AI-BS Broadcast Studio\` (and `frontend/desktop-build/win-unpacked`).

---

### 3. Documentation & Architectural Ledgers
- Update [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///c:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md).
- Update [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///c:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md) and bump version to `v5.148.0`.
- Update top-level historical index [MASTER_HISTORICAL_INDEX.md](file:///c:/AI-BS/MASTER_HISTORICAL_INDEX.md).

---

## Verification Plan

### Automated Build & Syntax Checks
- Run `npm run lint` and `npm run build` in `BroadcastStudioApp` to verify 0 syntax/bundling errors.
- Verify that `dist-electron/win-unpacked/AI-BS Broadcast Studio.exe` launches clean BS-Studio with Broadcast and DAW.

### Manual Verification
- Test switching between Broadcast Solo, DAW Solo, and Dual Broadcast + DAW split layouts.
- Verify Tone.js audio graph and DAW master bus routing into Broadcast Channel 3.
