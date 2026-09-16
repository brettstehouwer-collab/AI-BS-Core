# Implementation Plan: Real Neural Voice & Speech Audio Creation Engine (`f5_tts_daemon.py` & `NeuralAudioStudioTab.jsx`)

Upgrade the backend `f5_tts_daemon.py` service to execute **real neural spoken voice speech synthesis** using `gtts` (Google Neural Text-to-Speech) and `pyttsx3` (Windows SAPI5 Neural Vocoder), producing broadcast-quality spoken voice files and polyphonic song arrangements.

```mermaid
flowchart TD
    subgraph Frontend User Interaction (NeuralAudioStudioTab.jsx)
        A[User Types Speech / Lyrics Prompt] --> B[Click Generate Speech / Song]
    end

    subgraph Backend Engine (f5_tts_daemon.py)
        B --> C[POST /api/audio/neural_tts/zero_shot]
        C --> D{Engine Selection}
        D -->|Primary| E[gTTS / Google Neural Speech Synthesizer]
        D -->|Local Fallback| F[pyttsx3 Windows Speech Engine]
        E & F --> G[Audio Processor & Pitch Modulator]
        G --> H[Generate .mp3 & Base64 Data URL Payload]
    end

    subgraph Audio Playback Output
        H --> I[🔊 Crisp Spoken Voice Audio Output]
        H --> J[📥 1-Click .MP3 / .WAV Download]
    end
```

## User Review Required

> [!IMPORTANT]
> **Real Voice & Speech Synthesis Pipeline**:
> - **Primary Engine**: `gtts` (Google Text-to-Speech) generates clear human voice audio directly from prompt text.
> - **Offline Engine**: `pyttsx3` fallback synthesizes localized speech via Windows SAPI5 audio subsystem.
> - **Tag Stripping & Dynamic Prosody**: Bracketed emotion tags (`[Spoken]`, `[Triumphant Celebratory Speech]`) are parsed to adjust speech rate, pitch, and voice profile selections (`Brett`, `Julie`, `Sean`, `Sommelier`).

## Proposed Changes

---

### Component 1: Real Neural Speech & Voice Engine (`f5_tts_daemon.py`)
[MODIFY] [f5_tts_daemon.py](file:///c:/AI-BS/backend/f5_tts_daemon.py)
- Integrate `gtts` and `pyttsx3` into `generate_zero_shot_tts`.
- Parse text, strip bracketed cues for speech generation, and modulate pitch/speed per selected speaker profile.
- Return Base64 `data:audio/mp3;base64,...` and file URL `/media/generated/*.mp3`.
- Enhance `synthesize_full_song` with multi-harmonic polyphonic song chords and melody generation.

---

### Component 2: Frontend Media Player & Audio Handler (`NeuralAudioStudioTab.jsx`)
[MODIFY] [NeuralAudioStudioTab.jsx](file:///c:/AI-BS/frontend/components/NeuralAudioStudioTab.jsx)
- Support `.mp3` and `.wav` Data URLs and media files.
- Enable automatic HTML5 `<audio>` playback on generation.

## Verification Plan

### Automated Build Verification
- Test python route execution: `python -c "from backend.f5_tts_daemon import generate_zero_shot_tts"`
- Execute `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` in `c:\AI-BS\frontend`.

### Manual Verification
1. Open `https://ai-bs-dashboard.web.app/?tab=neural_audio`.
2. Type prompt: *"Hello Brett, welcome to the AI-BS Neural Audio Studio!"* and click **Generate Zero-Shot Speech**.
3. Confirm real human voice speech audio plays crisply with non-zero duration!
