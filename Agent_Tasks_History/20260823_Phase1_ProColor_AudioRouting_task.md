# BS-Studio Mega-Upgrade Tasks

## Phase 1: Professional Color & Advanced Audio Routing

- `[x]` **Color Grading Module**
  - `[x]` Scaffold `ColorGradingTab.jsx` or similar component inside BS-Studio.
  - `[x]` Build 3-Way Color Wheels UI (Shadows, Midtones, Highlights).
  - `[x]` Build WebGL Scopes (Waveform, Vectorscope, RGB Parade).
  - `[x]` Integrate Color Module into the BS-Studio layout/navigation.
- `[x]` **Advanced Audio Routing & Automation**
  - `[x]` Upgrade `dawStore` to support Aux Sends, Sub-busses, and Sidechain routing.
  - `[x]` Integrate these routing changes with `Tone.js` inside the audio engine.
  - `[x]` Build UI for drawing automation curves (Volume, Pan, FX) on audio regions in the timeline.
- `[ ]` **Verification & Polish**
  - `[ ]` Test Color Grading adjustments.
  - `[ ]` Test Audio routing (ensure no latency loops).
  - `[ ]` Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
  - `[ ]` Update `AI_BS_MASTER_ECOSYSTEM_MANUAL.md` and bump version.
  - `[ ]` Deploy to Firebase Hosting (`npm run build; firebase deploy --only hosting --non-interactive`).
  - `[ ]` Archive task and plan to master logs.
