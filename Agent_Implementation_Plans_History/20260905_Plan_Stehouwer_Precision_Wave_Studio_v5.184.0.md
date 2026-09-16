# Implementation Plan: Stehouwer Precision Wave Studio (v5.184.0)

## Problem & Background
The user requested a multi-track linear audio recording and waveform splicing workflow tailored specifically to them, with 100% original Stehouwer branding:
- Ingest full songs via drag-and-drop onto linear tracks.
- Splice, adjust, cut, copy, paste, and silence audio with precision.
- Dedicated tools (Selection, Envelope, Draw, Zoom, Time Shift, Multi-Tool).
- Hardware mic recording with real-time waveform display.
- Built-in DSP effects (Noise reduction, Normalize, Vocal isolation / Karaoke, Fade In/Out, Reverse).

## Architectural Design
1. **Linear Waveform Editor (`StehouwerWaveStudio.jsx`):**
   - High-performance canvas rendering min/max audio peaks downsampled at 60fps.
   - Dual-channel stereo L/R waveforms or mono channels.
   - Timecode ruler (mm:ss.ms) and amplitude vertical ruler (-1.0 to +1.0 / dB).
2. **Splicing & Editing:**
   - Split at Cursor (`Ctrl+I`), Cut (`Ctrl+X`), Copy (`Ctrl+C`), Paste (`Ctrl+V`), Silence (`Ctrl+L`), Trim Outside (`Ctrl+T`), Duplicate (`Ctrl+D`).
   - Time Shift tool (`F5`) to slide audio clips freely along track lanes.
3. **Live Stem Recording:**
   - Microphone input recording via `navigator.mediaDevices.getUserMedia`.
4. **DSP Processing Suite:**
   - Spectral noise profiling and filtering, peak normalizer, vocal isolation matrix, envelopes, and phase inversion.
5. **Original Branding:**
   - "Stehouwer Sound Lab", "Stehouwer Precision Wave Studio", "Stehouwer Master Export". Zero third-party trademark names.
6. **Deployment & Synchronization:**
   - Mirrored across all frontend component directories.
   - Version parity: v5.184.0 across headers.
   - Deployed live to Firebase Hosting (`ai-bs-dashboard.web.app`).
   - Synced Master Ledger, Ecosystem Manual, and Chronologies.
