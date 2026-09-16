# Implementation Plan: Neural Audio & Music Studio UI (`NeuralAudioStudioTab.jsx`)

Plan to create and integrate the missing **Neural Audio & Music Studio** component (`NeuralAudioStudioTab.jsx` & `NeuralAudioStudioTab.css`), exposing the backend `f5_tts_daemon.py` zero-shot voice cloning, Suno polyphonic music synthesizer, and BigVGAN mastering engine in a dedicated visual workspace under **Hub 4: Creator Studio & Revenue**.

```mermaid
flowchart TD
    subgraph Frontend UI (NeuralAudioStudioTab.jsx)
        A[🎙️ Zero-Shot Voice Cloning Tab]
        B[🎵 Suno Polyphonic Song Generator Tab]
        C[👥 Voice Profiles Vault & Cloning Tab]
        D[🎛️ BigVGAN Master EQ & Limiter Pass]
    end

    subgraph Backend DAEMON Bridge
        E[POST /api/audio/neural_tts/zero_shot]
        F[POST /api/audio/music/synthesize]
        G[GET & POST /api/audio/voice_profiles/*]
        H[POST /api/audio/mastering/process]
    end

    A --> E
    B --> F
    C --> G
    D --> H
    E & F & G & H --> I[📻 Broadcast 44.1kHz Audio Player & WAV/MP3 Downloader]
```

## User Review Required

> [!IMPORTANT]
> **Dedicated Navigation Hub Integration**: We will register `neural_audio` ("🎙️ Neural Audio & Music Studio") under **Hub 4: Creator Studio & Revenue** in `navigationConfig.js`, `App.jsx`, and `UniversalCommandPalette.jsx`.

> [!TIP]
> **Dynamic Cue Shortcuts**: The UI includes 1-click emotion tag chips (`[Triumphant Celebratory Speech]`, `[Spoken Word]`, `[Ecstatic]`, `[Whisper]`, `[Verse]`, `[Chorus]`) that auto-insert structured Suno & ElevenLabs tags into text prompts.

## Open Questions

> [!NOTE]
> None. All backend routes in `f5_tts_daemon.py` are active and compiled.

## Proposed Changes

---

### Component 1: Dedicated Neural Audio & Music Studio Component & Stylesheet
[NEW] `frontend/components/NeuralAudioStudioTab.jsx` (file:///c:/AI-BS/frontend/components/NeuralAudioStudioTab.jsx)
[NEW] `frontend/components/NeuralAudioStudioTab.css` (file:///c:/AI-BS/frontend/components/NeuralAudioStudioTab.css)

Features:
- **Zero-Shot Speech Synthesizer**: Text input, speaker profile selector (`Brett`, `Julie`, `Sean`, `Professional Anchor`, `Italian Sommelier`), emotion chips, dynamic audio waveforms, and 1-click MP3/WAV download.
- **Suno Polyphonic Song Studio**: Structured lyric editor with section markers (`[Verse]`, `[Chorus]`, `[Bridge]`), BPM counter, key signature selector, and multi-track preview.
- **Voice Profiles Vault**: Visual profile cards with gender, pitch base, and 1-click voice enrollment from reference audio.
- **DSP Audio Master Deck**: Soft-knee true-peak limiter (-1.0 dBFS) and LUFS normalization sliders.

---

### Component 2: System Routing & Access Control
[MODIFY] [navigationConfig.js](file:///c:/AI-BS/frontend/components/navigationConfig.js)
- Register `neural_audio` ("🎙️ Neural Audio & Music Studio") under **Hub 4: Creator Studio & Revenue**.

[MODIFY] [App.jsx](file:///c:/AI-BS/frontend/App.jsx)
- Register lazy import: `const NeuralAudioStudioTab = safeLazy(() => import('./components/NeuralAudioStudioTab.jsx'));`
- Add `neural_audio` to `TAB_COMPONENTS` array.

[MODIFY] [UniversalCommandPalette.jsx](file:///c:/AI-BS/frontend/components/UniversalCommandPalette.jsx)
- Add quick action `"Open Neural Audio & Music Studio"`.

## Verification Plan

### Automated Build Verification
- Execute `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` in `c:\AI-BS\frontend` to ensure 0 build errors.

### Manual & Functional Verification
1. Open `https://ai-bs-dashboard.web.app/?tab=neural_audio`.
2. Generate zero-shot speech with `[Triumphant Celebratory Speech]` tag and verify 44.1kHz playback.
3. Test Suno song synthesis and profile list retrieval.
