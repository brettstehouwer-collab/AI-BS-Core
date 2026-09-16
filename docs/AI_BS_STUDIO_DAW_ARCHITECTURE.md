# AI-BS Studio: Digital Audio Workstation Architectural Manual

AI-BS Studio is a comprehensive digital audio workstation (DAW) integrated into the AI-BS ecosystem. Its unique, non-linear, pattern-based workflow sets it apart from traditional linear DAWs.

---

## 🏛️ The Five Main Windows (Core Interface)

The AI-BS Studio ecosystem is built around five standalone windows that interconnect to take a sound from a raw idea to a finished master track:

### 1. The Channel Rack (`F6`)
- **Role:** Starting point for all sound generation. Houses every synthesizer, sampler, or plugin generating sound.
- **Step Sequencer:** Grid layout of steps representing beats and bars for scheduling rhythmic hits.
- **Pattern-Based Architecture:** Everything built inside the Channel Rack creates a "Pattern" for modular arrangement.
- **Target Mixer Track:** Individual routing box linking specific instruments to designated Mixer insert tracks.

### 2. The Piano Roll (`F7`)
- **Role:** Industry-standard composition grid for complex musical sequencing.
- **Melody & Chords:** Grid aligned with a piano keyboard layout for drawing, slicing, stretching, and moving notes.
- **Note Properties (Graph Editor):** Fine-grained per-note automation for Velocity, Pitch, and Panning.
- **Slide Notes:** Native pitch gliding for 808 slides and smooth melodic transitions.

### 3. The Playlist (`F5`)
- **Role:** Song arrangement canvas and master timeline.
- **Arrangement Tracks:** Unrestricted multi-clip stacking (Patterns, Audio Clips, and Automation Clips on shared tracks).
- **Pattern Clips:** Arrangement blocks assembled from the Channel Rack.
- **Audio Clips:** Dedicated housing for recorded vocals, live stems, and external samples.

### 4. The Mixer (`F9`)
- **Role:** Sonic balance, spatial depth, and acoustic texture control.
- **Insert Channels:** Dedicated channel strips with independent volume faders, stereo panning, and send routing.
- **10 Serial Effects Slots:** Modular audio processing chain (EQ → Compression → Reverb → Limiting).
- **Master Track:** Summing bus for project-wide processing and final mastering DSP.

### 5. The Browser (`Alt / Opt + F8`)
- **Role:** Navigational file explorer and asset vault.
- **Asset Access:** Direct auditioning of sample packs, drum kits, VST3 presets, and stem archives.
- **AI-BS Cloud Vault:** Integrated, searchable cloud and local drive library with automatic tempo stretching.

---

## 🛠️ Essential Built-In Creation Tools
- **Automation Clips:** Visual spline curves on the Playlist automating any plugin parameter over time.
- **Edison Wave Editor:** In-slot audio recorder, spectral analyzer, pitch detector, and sample slicer.
- **Stem Separation:** Machine learning engine splitting mixed stereo audio into 4 stems (Vocals, Drums, Bass, Instruments).
- **Fruity Slicer / Slicex:** Transient-based beat chopping and keyboard re-sequencing.
- **Tool Menu Macros:** Automated session cleanup scripts (Smart Disable all plugins, purge unused clips).

---

## 🔌 Standout Stock Plugins & Processors

| Plugin Name | Category | Primary Function |
|---|---|---|
| **FLEX** | Synth (Generator) | Preset-based advanced synthesizer for acoustic and electronic sounds. |
| **Sytrus** | Synth (Generator) | FM and additive synthesizer for sound design, heavy basslines, and leads. |
| **FPC** | Sampler (Generator) | 16-pad MPC-style virtual drum machine with multi-layered velocity mapping. |
| **Fruity Parametric EQ 2** | Effect | Visual 7-band parametric equalizer for surgical frequency carving. |
| **Gross Beat** | Effect | Time and volume buffer processor for sidechain gating, glitch, and half-time. |
| **Fruity Limiter** | Effect | Precision limiter, compressor, and sidechain processor for master ceiling control. |
