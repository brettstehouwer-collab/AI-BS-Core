# BS-Studio: Master Feature & Capabilities Overview (v5.66.1)

BS-Studio has evolved into a hyper-advanced, web-based digital audio workstation (DAW) and video non-linear editor (NLE) that rivals native desktop software. By leveraging modern web APIs (WebRTC, WebAudio, Canvas) bridged dynamically with local Python daemons, BS-Studio offers a fully sovereign, professional production environment.

Here is the comprehensive breakdown of all features and modules currently active in the studio.

---

## 🎛️ 1. Neural DAW & Sound Synthesis (The Audio Engine)
At its core, BS-Studio operates as a fully functional, browser-based DAW utilizing `Tone.js` and `zustand` for high-performance audio scheduling and state management.

- **Modular UI Architecture:** Built to mirror the workflow of FL Studio, featuring a distinct **Channel Rack**, **Step Sequencer**, **Piano Roll**, **Mixer**, and a linear timeline **Playlist**.
- **Native Synthesizers:** Includes built-in algorithmic synthesizers (Sub-Bass, Kicks, Snares, Hi-Hats, Cyber Leads) that generate audio mathematically in real-time.
- **Shared Cloud Drive Asset Browser:** A drag-and-drop media browser that dynamically fetches `.wav`, `.mp3`, and `.mp4` files directly from the AI-BS Shared Cloud Drive. Users can instantly stream/audition audio or drag media directly onto the timeline tracks.
- **Live Microphone Injection:** Uses `Tone.UserMedia` to record live microphone audio and inject the raw data directly into the active timeline buffer.
- **Interactive Sound Designer:** A per-channel modal that gives you access to a 3-band parametric EQ (`Tone.EQ3`) and visual ADSR envelope sliders to manipulate synthesizer parameters dynamically.
- **Generative AI Prompt-to-MIDI:** An LLM-driven module embedded above the Piano Roll capable of mathematically generating MIDI patterns and drum grooves based on natural language prompts.

## 🎚️ 2. Advanced Audio Routing & VST3 Handoff (The Mixer)
The audio signal chain in BS-Studio is designed for professional routing and external hardware integration.

- **Parallel FX Send Busses:** Audio is no longer processed linearly on every channel. BS-Studio features dedicated 100% wet send busses (Reverb, Delay) connected to the master. Channels use horizontal send sliders in the Mixer to route dry signals into these shared spatial rooms.
- **Vocal Pitch Correction:** Global `Tone.PitchShift` nodes have been added to the master rack, allowing for immediate vocal pitch-snapping and formant manipulation.
- **Native VST3 Plugin Bridging:** Perhaps the most groundbreaking audio feature—BS-Studio bridges the web sandbox to your native operating system. It uses a custom `VSTBridgeNode` to stream `Float32` audio arrays over a WebSocket to a local Python daemon (`aibs_vst_daemon.py`). This daemon, utilizing Spotify's `pedalboard` engine, processes the audio through your local Windows VST3 plugins (`E:\AI_BS_Resources\VST3_Plugins`) in real-time with virtually zero latency.

## 🎨 3. Pro Color Grading & Visual Scopes (The Video Engine)
BS-Studio is not just a DAW; it is a broadcast-grade video editor.

- **Non-Linear Timeline Video Editing:** The `Playlist` features dedicated V1/V2 video tracks situated above the audio. It includes professional editing tools like the Blade (`✂️ Cut`), Trim handles (`[ Trim L/R ]`), and a Magic Wand `Auto-Cut to Beat` that automatically slices video clips perfectly on Kick drum transients.
- **Whisper AI Subtitles:** Microphone recordings are automatically transcribed via `openai-whisper` on the backend, generating TikTok-style dynamic animated subtitles perfectly synced to the `Tone.Transport` timeline.
- **Broadcast Scopes:** Features real-time, Canvas-based RGB Parade, Waveform, and Vectorscope monitors to ensure your video content meets strict luma and chroma broadcast standards.
- **3-Way Color Wheels:** A professional grading module featuring Lift (Shadows), Gamma (Midtones), and Gain (Highlights) color wheels for precise, non-linear pixel manipulation.

## 🧬 4. Procedural Node-Based Compositing (The VFX Engine)
Moving beyond the linear timeline, BS-Studio incorporates a node-based visual compositor heavily inspired by DaVinci Resolve's Fusion and Nuke.

- **Node Graph UI:** Built on `@xyflow/react`, allowing users to visually wire Video Sources into Color Transforms, Blurs, and AI Generative Fill nodes.
- **Procedural Pipeline:** Edits are procedural and non-destructive. The node graph acts as the mathematical instruction set that manipulates the visual payload before it hits the master output monitor.
- **Hybrid View:** A dedicated workspace view that splits the screen, showing the active Video Monitor, the linear Timeline, and the Node Graph simultaneously.

## 📡 5. Hybrid Export & Live Broadcast (The Egress Pipeline)
The final pillar of BS-Studio is its ability to break out of the browser and interface with industry-standard ecosystems.

- **Live NDI Broadcast to OBS:** Using HTML5 `captureStream()` and WebRTC, the studio's master video/audio `<canvas>` is fed directly into a local Python daemon (`aibs_broadcast_daemon.py`), which immediately translates the signal into an NDI source. This allows you to use BS-Studio as a generative visual layer inside OBS for live streaming.
- **FFmpeg NVENC Master MP4 Export:** Render your timeline into a highly compressed, hardware-accelerated MP4. The frontend renders the offline audio mix, submits it with the video payloads to the backend, and multiplexes the final A/V via `ffmpeg -c:v h264_nvenc`.
- **Pro Industry Export (FCPXML & AAF):** Users can export their timelines to `FCPXML` (for Adobe Premiere, Final Cut, DaVinci Resolve) and `AAF` (for Pro Tools, Media Composer).
- **Hybrid "Raw vs Baked" Handoff:**
  - **Raw Metadata Filters:** Generates the timeline XML and automatically translates standard BS-Studio node effects (Color, Blur) into native FCPXML `<filter-video>` elements, so the grade carries over natively to Premiere/Resolve.
  - **Baked Proxy Renders:** For complex AI Generative Fill nodes that offline software cannot understand, the export engine stubs a `<asset>` reference for a flattened proxy video, treating the generative VFX as a baked asset.

---
> [!IMPORTANT]
> **Architectural Status:** As of v5.66.1, all components listed above are live, fully integrated into `ai-bs-dashboard.web.app`, and synchronized across the local AI-BS daemons and SQLite master ledgers.
