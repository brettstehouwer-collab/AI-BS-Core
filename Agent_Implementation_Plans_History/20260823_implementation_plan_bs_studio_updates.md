# BS-Studio Matrix Update (Phase 2)

We are about to undertake a massive architectural expansion of the BS-Studio DAW. Building "all of them" requires systematically upgrading `Tone.js` data flows and adding several new UI layers.

## Goal
To implement the 4 core pillars of the BS-Studio Phase 2 roadmap:
1. Live QWERTY & USB MIDI Input + 60FPS Frequency Spectrum Visualizer
2. Prompt-to-MIDI AI Generator
3. Live Microphone Vocal Recording
4. Interactive Parametric EQ & ADSR Sound Designer

## Proposed Architecture

### Phase 1: Engine Upgrades & Visualizer (dawStore.js & UI)
- **QWERTY Controller Engine:** We will add global `keydown`/`keyup` event listeners in `dawStore.js` mapped to a 2-octave keyboard layout (e.g., A=C3, W=C#3, S=D3) that triggers the active synthesizer.
- **Web MIDI API:** Implement `navigator.requestMIDIAccess()` to intercept USB keyboard inputs, map the MIDI note values to frequencies, and trigger the synths with zero latency.
- **60FPS Spectrum Visualizer:** We will attach a `Tone.FFT` or `Tone.Analyser` node to the Master output bus. We will render this onto an HTML5 `<canvas>` using `requestAnimationFrame` to draw glowing cyan/violet frequency bands in the top transport bar of `MusicDAWStudioTab.jsx`.

### Phase 2: AI Prompt-to-MIDI Generation
- **UI:** A glowing "AI Compose" prompt bar situated above the Piano Roll.
- **Logic:** An integration that accepts a prompt (e.g., "dark trap melody"), queries the LLM/backend, and parses returned JSON into `Tone.js` Sequence data. *(Note: We will initially simulate the LLM return payload to guarantee perfectly snapped MIDI loops before hooking up the physical backend).*
- **State Injection:** The returned MIDI arrays will automatically overwrite the active Channel Rack sequencer state.

### Phase 3: Interactive Sound Designer (ADSR & EQ)
- **UI Element:** A new `SoundDesigner.jsx` panel that slides up from the bottom or opens as a modal when clicking an instrument in the Channel Rack.
- **Features:** 
  - 4 vertical sliders for Attack, Decay, Sustain, Release (wired directly to `Tone.Synth.envelope`).
  - A 3-band interactive EQ mapping to a dedicated `Tone.EQ3` node per channel.

### Phase 4: Live Microphone Recording
- **Engine Setup:** Utilize `Tone.UserMedia()` to request microphone access and `Tone.Recorder()` to capture the stream.
- **Playlist UI:** Add a dedicated "Vocal Takes" audio track in `Playlist.jsx`.
- **Workflow:** Hitting "Record" on the transport captures the mic, and hitting "Stop" automatically extracts the `.wav` Blob, renders a placeholder waveform, and places it on the Playlist timeline in sync.

---

> [!WARNING]
> **Performance Note for 60FPS Visualizer:**
> Running a fast Fourier transform (FFT) and `<canvas>` loop can consume frontend CPU. I will heavily optimize the drawing loop using `useRef` to prevent React from re-rendering the whole DAW every frame.

> [!IMPORTANT]
> **Microphone Permissions:**
> To use the Live Mic recording, the browser will pop up a strict "Allow Microphone" dialog. You must click **Allow** for `localhost` / Firebase to test this feature.

## Open Questions / User Review Required
1. For the **AI Prompt-to-MIDI**, I will build the frontend UI and wire it to a mocked "local" generation function that auto-fills the grid so we can test the UI perfectly. Are you okay with starting with a simulated AI output before we wire it to the `stehouwer_llm` backend?
2. Shall we begin Phase 1 (MIDI + Visualizer) as soon as you hit Proceed?
