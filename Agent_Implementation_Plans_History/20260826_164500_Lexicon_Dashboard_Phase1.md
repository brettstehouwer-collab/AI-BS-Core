# Theatrical Matrix Orchestration: Lexicon to A/V Pipeline

This plan outlines the logical sequence for expanding the AI-BS architecture to connect our newly built Lexicographical Vault to real-time UI, video, and audio systems.

## Master Sequence Rationale
The most logical sequence follows the path of **Visibility** -> **Visual Impact** -> **Abstract Automation**.
1. **Phase 1: UI/UX (Visibility)** - We must first be able to *see* the Lexicon engine working. Visualizing the semantic pipeline gives us a real-time debugging interface for word substitutions and expansions.
2. **Phase 2: OBS Orchestration (Visual Impact)** - Once we can see the semantic triggers working in the UI, we bind those exact text/semantic triggers to swap OBS scenes and toggle ComfyUI visual overlays. 
3. **Phase 3: VST/Audio Bridge (Abstract Automation)** - Finally, we hook the most abstract layer—Audio. The Lexicon semantics will trigger MIDI commands and VST parameter automations, completing the full Theatrical Matrix loop.

---

## Phase 1: Frontend Lexicon & Theatrical Dashboard (UI/UX)
**Goal:** Build a dynamic UI panel in the Primary React Dashboard that visualizes the Persona Engine's real-time word substitutions, semantic expansions, and "bullshit heuristics".

### Proposed Changes

#### [NEW] `frontend/src/components/LexiconTheatricalDashboard.jsx`
- Create a real-time dashboard component.
- Implement polling or WebSocket subscription to visualize active LLM inferences.
- Render a live "Semantic Expansion Map" using the `POST /lexicon/enrich` endpoint we built today.

#### [MODIFY] `frontend/src/App.jsx` (or Sidebar navigation)
- Inject the new `LexiconTheatricalDashboard` route into the core UI matrix so it's easily accessible alongside the `MatrixDoctorTab`.

---

## Phase 2: OBS Theatrical Orchestration (Video)
**Goal:** Expand `aibs_obs_orchestrator.py` to listen to the Lexicon-infused Persona Engine and automate scene swaps and visual overlays.

### Proposed Changes

#### [MODIFY] `backend/aibs_obs_orchestrator.py`
- Import and integrate `LexiconService`.
- Build a semantic listener: when the LLM generates specific Lexicon categories (e.g., "aggressive words" vs "calm words"), map these states to specific OBS scenes.
- Expose WebSocket endpoints for the LLM inference engine to trigger OBS macros based on vocabulary used.

---

## Phase 3: The VST/Audio Lexicon Bridge (Audio)
**Goal:** Bind specific semantic Lexicon categories to trigger MIDI commands or VST parameter automations in real-time.

### Proposed Changes

#### [MODIFY] `backend/aibs_vst_daemon.py`
- Create an NLP-to-Audio translation layer.
- Map Lexicon semantic "moods" (derived from the Persona Engine) to specific MIDI CC values (e.g., higher tension words = higher cutoff frequency on a VST synth).
- Ensure zero-latency bridging through the `8013` VST bridge port.

---

> [!IMPORTANT]
> **User Review Required**
> I recommend we execute this plan one phase at a time to ensure maximum stability. We will begin exclusively with **Phase 1 (Frontend Lexicon & Theatrical Dashboard)**. Once that is built, tested, and visually confirmed, we will move to Phase 2.
>
> If this sequence and plan look correct to you, hit **Proceed** and I will immediately begin executing Phase 1.
