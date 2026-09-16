# BS-Studio Mega-Upgrade: Phase 3 Plan

This document outlines the architecture for Phase 3 of the BS-Studio upgrade: **Broadcast, Live, & Pro Workflows**. The goal is to deeply integrate BS-Studio with professional industry environments, including OBS/vMix (via NDI), Pro Tools/Premiere Pro (via XML exports), and native Windows VST3 plugins.

## User Review Required

> [!IMPORTANT]
> The Native VST Bridge will require spinning up a new Python daemon (`vst_daemon.py`) using the `pedalboard` library to load standard Windows `.vst3` files. This daemon will communicate with `Tone.js` in the browser via WebSockets. Please confirm if you have a specific folder path where you keep your VST3 plugins (e.g., `C:\Program Files\Common Files\VST3`).

## Open Questions

> [!TIP]
> 1. For **Live NDI / OBS Integration**, do you want a button that streams the main Video Preview monitor directly to a virtual camera/NDI output in real-time, or should it just bridge to the existing `aibs_broadcast_daemon.py`?
> 2. For **Industry Export Formats**, we will start with FCPXML (Final Cut Pro XML), which imports cleanly into Premiere Pro and DaVinci Resolve. Is this the preferred format, or do you require AAF/OMF specifically for Pro Tools right out of the gate?

## Proposed Changes

---

### 1. Native VST3 Plugin Bridge

#### [NEW] [backend/vst_daemon.py](file:///C:/AI-BS/backend/vst_daemon.py)
A lightweight FastAPI/WebSocket Python daemon utilizing the Spotify `pedalboard` library. 
- Loads local VST3 plugins.
- Accepts raw audio chunks from the frontend (Tone.js), processes them through the VST, and returns the wet signal in real-time.

#### [MODIFY] [frontend/src/components/daw/dawStore.js](file:///C:/AI-BS/frontend/src/components/daw/dawStore.js)
- Add a new `VSTNode` class that extends Tone.js to interface with the `vst_daemon.py` via WebSocket.
- Allow users to select a VST plugin from the Mixer inserts.

---

### 2. NDI & Live OBS Streaming

#### [MODIFY] [frontend/src/components/daw/VideoPreviewMonitor.jsx](file:///C:/AI-BS/frontend/src/components/daw/VideoPreviewMonitor.jsx)
- Add a "Broadcast to OBS" toggle.
- When enabled, capture the `<canvas>` stream and pipe it to the backend via WebRTC/WebSocket to be picked up by the `aibs_broadcast_daemon.py` (which already handles DXGI/Virtual Camera).

---

### 3. Industry Export Formats (FCPXML)

#### [MODIFY] [frontend/src/components/daw/MusicDAWStudioTab.jsx](file:///C:/AI-BS/frontend/src/components/daw/MusicDAWStudioTab.jsx)
- Add an `Export FCPXML` button next to the Export MP4/WAV buttons in the top Master Transport Bar.
- Implement an XML generator function that parses `useDawStore.getState().videoTracks` and `playlistTracks` into a standard Apple FCPXML `.fcpxml` document.
- Triggers an automatic download, allowing the user to seamlessly drop the AI-BS timeline into Premiere Pro or DaVinci Resolve with all cuts preserved.

## Verification Plan

### Automated Tests
- Validate that the generated FCPXML structure strictly adheres to the DTD schema.

### Manual Verification
- We will deploy the `vst_daemon.py`, load a standard VST3 plugin (like a free EQ or Reverb), and route a channel through it to verify round-trip WebSocket latency.
- We will click "Export FCPXML" and verify the resulting file opens correctly in a professional NLE, maintaining clip positions and trims.
