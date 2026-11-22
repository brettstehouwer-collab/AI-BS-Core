# October7 audio, recording and creative-workflow audit — 2026-10-31

## Scope and evidence

Read-only inspection of recovered editable source plus installed browser assets. No executable, GUI, microphone, speaker, hardware device, VST plugin, AI server, installer, or external endpoint was started. No original media was decoded or changed. The reproduction helper executes selected AST definitions with synthetic NumPy arrays and inert file/dialog substitutes; it does not import the application. No crypto configuration, service, or Google Drive content was changed by this audit subtask.

Authoritative native source: `C:\Users\footb\OneDrive\Desktop\carrytodex\VOICECOACHF\app_native.py`, SHA-256 `050ea0cdd76f8942799df21c4559ffa021647e25f2e126db7b2079971bc1e72f`. The package audit independently established compiled-code equivalence with installed `October7_VocalStudio_Native.exe`; see `..\package\source_equivalence.json`. This establishes source relevance, not runtime or hardware verification.

Browser asset: `C:\Program Files\October7_VocalStudio_DAW\VOICECOACH PROGRAM.html`, SHA-256 `48bf3db02931ba4cc4d5efdf85818f6fa51074c7ac9dc39cea42a9b1764d2a52`. The `_internal` HTML has a different SHA-256 (`df8d7f656bc7c7dad81d5c8076decd758ffe79a285fe2910dda9c2fc1c604226`). The browser and native programs are separate implementations; do not treat a fix to one as a fix to the other.

Reproduction command: `python C:\AI-BS\backups\october7_audit212\audio\prove_native_audio212.py`. Result: seven deterministic defect reproductions completed successfully. Machine-readable observations are in `offline_evidence212.json`. These are tests proving existing failures, not a claim that product fixes or device tests passed.

## What the program actually builds

The source describes a personal, song-centered vocal rehearsal and production workstation: one backing arrangement, a timed lyric/breath prompter, four vocal lanes (lead, left/right doubles, harmony), microphone monitoring and recording, playback transport, a vocal effects rack, waveform/pitch feedback, and WAV exports. The browser edition additionally contains takes, section comping, MIDI transcription requests, stem separation, backing generation, and lyric-assistant requests to a local Python bridge. The native edition instead has a direct sounddevice audio engine and a Pedalboard VST3 insert.

This is an identifiable product direction: rehearse a song with cues, record layered takes, compare the performance, create a comp, balance the parts, and export a reusable mix. Several native controls are currently visual descriptions rather than connected functions. The evidence does not support calling this a finished general-purpose DAW, validated vocal coach, full synthesizer, or automatic medical/acoustic diagnosis system.

## Native executable: high findings

### N01 — Recordings silently stop retaining audio after 10 seconds — VERIFIED / reproduced / HIGH

`app_native.py:386–388` allocates a 480,000-frame recording ring. The callback at `419–441` writes samples at `430–431` but ignores the accepted-frame count. Only `save_recorded_take`, called after Record is stopped, reads the ring (`590–598`). There is no recording writer draining it while recording. A twelve-second synthetic recording retains 479,999 frames (9.999979 seconds) and loses 96,001 frames without an error. Longer takes lose everything after the first ten seconds. The UI does not warn about this limit.

Remediation: continuously drain a bounded capture queue on a dedicated writer into a uniquely named temporary lossless take; account for short writes and device overflow explicitly; finalize atomically with metadata and a recoverable journal. Keep the raw input immutable; apply monitoring effects separately. Merely enlarging the ring increases the time before loss and does not provide durability.

### N03 — Prefetch reaching EOF stops playback before queued audio is consumed — VERIFIED / reproduced / HIGH

`_playback_feeder_worker` uses its producer cursor at `457–464` to set `is_playing=False` before the ten-second output ring drains. The callback reads that ring only while `is_playing` (`435–437`). The synchronous proof queues a one-second track, then observes transport stopped with 49,152 frames still queued and no consumption. Actual truncation depends on callback scheduling and track length; up to the queued lookahead can be discarded. This is a source-level ordering defect, not a measured device failure.

Remediation: distinguish producer EOF from consumer transport state; finish only after the final queued frame has been consumed. Keep lookahead short, record underruns, and derive the displayed cursor from the consumer clock.

### N04 — Both native WAV export buttons raise NameError on real content — VERIFIED / reproduced / HIGH

`_export_stems_wav` references undefined `HAS_SOUNDFILE` at `1575`; `_export_master_mix_wav` does so at `1605`. `soundfile` is imported unconditionally, and no capability flag is defined. Each isolated export with a nonempty synthetic track raises `NameError: name 'HAS_SOUNDFILE' is not defined`; no file is written.

Remediation: remove the nonexistent capability branch or define a genuine dependency capability at import, fail visibly when unavailable, and announce success only after the file closes successfully. Catch storage/format exceptions with useful paths, without claiming completion.

### N07 — Track arm controls do not select recording destination — VERIFIED / reproduced / HIGH

Track REC toggles only change `tracks[name]['armed']` (`757–763`). `toggle_rec` at `1397–1411` never consults those flags and always loads the saved take into `Lead Vocal` (`1410`). The proof arms Harmonies and disarms Lead, then Stop still loads Lead. This silently replaces the active lead buffer in memory. Raw saved files may remain, but there is no take catalogue or automatic recovery of the displaced track assignment.

Remediation: validate exactly the intended recording lanes before starting, capture that selection in a take session, and associate the completed take with those lanes; preserve the previous take and offer an explicit comp/replace operation.

### N08 — Takes have no timeline origin and reload at song zero — VERIFIED / static / HIGH

The transport can seek to a section (`1424–1432`), then record. Recording writes a contiguous stream of samples (`430–431`), saves just that buffer (`590–598`) and loads it as a full-length Lead Vocal source (`1410`). There is no recorded start-sample, clip offset, latency offset, or pre-roll metadata. The mixer uses the global producer position to slice each track (`450`, `474–488`). Consequently a verse recorded after seeking is interpreted as audio beginning at time zero, and playback at the verse position can skip the entire short take.

Remediation: store per-clip source range and timeline start in samples, plus the device/sample-rate and measured latency context. Do not destructively pad or trim originals to approximate alignment.

### N09 — No durable project/session or crash-safe capture state — VERIFIED / static / HIGH

The native program reloads fixed packaged media (`1500–1519`); there is no project save/load representation for track-file assignments, mix settings, take history, cue changes, clip placement, or plugin state. Audio remains only in a ten-second ring until Stop. There is no close handler finalizing an active recording; `main` calls `engine.stop` only after the GUI returns (`1627–1628`), and `stop` does not save (`573–575`). A crash or closing while recording loses unsaved capture.

Remediation: per-user writable project directories, atomic versioned project manifests, append-only take registry, checkpointed capture and explicit interrupted-take recovery. Preserve external source references with optional managed copies. Never store user projects in an elevation-requiring installation directory.

## Native executable: medium and low findings

### N02 — Pitch/HNR analysis cannot run at configured callback size; no-signal UI fabricates a note — VERIFIED / reproduced / MEDIUM

The engine uses 48 kHz/128-frame blocks (`1621`). `_update_pitch_and_hnr` calculates a maximum lag of 800 samples, then requires `800 < len(corr)` at `359`. A 128-frame callback produces only 128 positive correlation lags, so the analysis body is unreachable. Tests with 110, 220, 440 and 880 Hz all leave f0 at zero. `update_telemetry:1445` then displays `A#3 228.6 Hz +3 cents` instead of unavailable. The waveform still updates, making the fabricated note particularly misleading.

Use a separate analysis accumulator with a sufficiently long window/hop, confidence and voiced/unvoiced state. Keep it off the low-latency audio callback. Clear or age out invalid measurements.

### N05 — Export ignores pan and differs from live monitoring — VERIFIED / reproduced after isolating N04 / MEDIUM

Live mixer `479–488` applies an equal-power pan law; master export `1592–1601` simply copies each mono track into both channels and ignores pan. A hard-left mono impulse exports `[0.25, 0.25]`, while live panning yields `[0.25, 0]`. Export also omits any monitor/VST/DSP graph and may normalize the entire mix (`1602–1604`); whether monitor effects should be committed needs an explicit product choice. Use one deterministic mix/render graph for preview and export with an explicit dry/processed mode.

### N06 — Solo controls are ignored by playback and export — VERIFIED / reproduced / MEDIUM

Solo toggles store a flag (`770–773`) that neither mix loop reads (`466–488`, `1592–1601`). In the proof, a silent soloed lane does not exclude a non-soloed lane (audible peak 0.141421). Apply the same solo/mute eligibility rules in playback and exports, and label any special solo-safe lanes.

### N10 — Native EQ/compressor UI is disconnected; echo, reverb and air are not implemented in the DSP — VERIFIED / static / MEDIUM

`_create_fx_card:1323–1359` builds checkboxes/sliders but connects neither to engine parameters. `process_block:292–341` implements high-pass, a scalar presence boost and compression only. Echo/reverb state and `air_gain` are allocated (`243`, `254–267`) but never processed. A broadband scalar is labeled as a 3.2 kHz presence filter. The visible cards at `980–1009` promise active frequency-selective EQ, delay and reverb regardless of these omissions.

Wire parameters through a validated control model, mark unsupported modules unavailable, and implement each processor with impulse/frequency-response tests before claiming it works.

### N11 — Performance scores and coaching statements are fixed examples presented as measurements — VERIFIED / static / MEDIUM

The UI hard-codes cadence 40%, pitch 64%, dynamics 73%, stamina 8% and grades at `1241–1245`, then fixed performance claims at `1258–1268`. No scoring updates appear in telemetry. Track Loaded/Mic Online/2.67 ms headers (`928–946`) also precede verified states. 128/48000 is one block period, not measured round-trip latency. Use clear unavailable/example states and show measurement source, confidence, time range, device state and analysis version.

### N12 — Cue editor's Save & Apply button discards all changes — VERIFIED / static / MEDIUM

`_edit_cues_dialog:1541–1566` fills a text editor and connects Save to `dlg.accept` only. It never reads text, validates it, modifies the song model or writes a project. The caller ignores `dlg.exec`'s result. Implement parse/validate/preview/apply with a persisted project model and undo.

### N13 — Mixer/control access is unsynchronized across GUI, producer and audio threads — VERIFIED race exposure / MEDIUM

The producer iterates a mutable `tracks` dictionary (`453`, `466`) while Add Stem inserts keys (`1496`), and GUI replaces audio arrays and changes cursor/ring pointers (`577–585`, `1416–1417`, `1425–1427`). Concurrent dictionary size changes can raise RuntimeError and terminate the unguarded feeder. `SPSCRingBuffer.clear:148–151` resets both pointers from the GUI, breaking its single-producer/single-consumer ownership. A producer epoch/control queue and immutable track snapshots can apply changes at safe boundaries; report worker failure instead of silently losing playback.

### N14 — Audio callback has unbounded/expensive work and blocks on plugin loading — VERIFIED code risk; not benchmarked / MEDIUM

The 2.67 ms callback executes a Python per-sample loop, allocations, waveform rolling, correlation, and VST processing (`419–441`, `292–340`). The plugin lock used inside callback (`207`) is also held during potentially slow plugin construction (`189–192`). Callback `status` is ignored. Allocate/pre-size buffers, move analysis out, keep device callback bounded, swap preloaded plugin state safely and surface overrun/underrun counters. Hardware capacity is not established by static inspection.

### N15 — Recording commits processed left channel only — VERIFIED / static / MEDIUM

The capture path processes EQ/compressor and stereo VST first, then writes only `vocal_stereo[:,0:1]` (`423–431`). A stereo plugin's right channel is irreversibly omitted from the saved take, and no dry recording is retained. Prefer dry mono/stereo raw capture plus non-destructive processing; make committed effects an explicit option.

### N16 — Loop/cursor state diverges; queued controls can lag — VERIFIED / static / MEDIUM

Producer loops reset `feeder_pos_samples` only (`457–460`), while callback continues increasing `play_pos_samples` (`437`). Timecode and lyrics use the latter (`1449–1473`), so after a loop they point beyond the song while audio restarts. Up to ten seconds can be prefetched, delaying mute/gain changes and metronome state. Loop and seek need one sample-accurate transport model and bounded lookahead.

### N17 — Audio import blocks the GUI, hides failures and may double the arrangement — VERIFIED / static / MEDIUM

Full-file decode/resample occurs on the GUI path (`577–588`, `1486–1519`), with exceptions printed only. Callers announce loaded on failure. Packaged separated `vocals/other/bass/drums` are automatically loaded into vocal lane names (`1505–1513`) and the complete original mix is also loaded as backing (`1515–1519`), so playing defaults can sum the original plus its source stems and clip/duplicate components. Preserve stem identities and choose either reconstructed stems or full backing, with explicit replacement and load results.

### N18 — Output-only/disconnected state can still start recording and claim microphone availability — VERIFIED / static / MEDIUM

`start` can return output-only or disconnected (`546–561`); Record never checks stream/input capability (`1397–1403`). Output-only callback constructs zeros (`420`), and the UI still says Mic Online. Start should expose capabilities and Recording should require a real selected input or display an explicit silent-input mode.

### N19 — Recording filename collision and unsafe finalization — VERIFIED / static / MEDIUM

Names use second-resolution time (`1407–1408`), allowing a quick second take to overwrite a previous one. `save_recorded_take:590–598` drains the only copy before opening/writing the file, has no rollback/temporary commit, and can fail on disk-full/permissions. UUID or collision-safe names and transactional finalize are required.

### N20 — Compressed initial envelope attenuates the beginning; sample-rate fallback is inflexible — VERIFIED / static / LOW/MEDIUM

Compressor envelope begins at 1.0 (`251`), while the threshold is ~0.063 (`247`), causing initial attenuation until the envelope decays. All fallback device candidates still demand 48 kHz/128 frames (`529–536`, `548–553`) instead of negotiating a supported configuration and reporting actual latency. Preserve requested vs obtained device settings and validate warm-start dynamics using test vectors.

### N21 — Default mic monitoring and MMCSS claims need explicit state — VERIFIED code facts / MEDIUM

Every callback adds microphone signal to outputs with no monitor switch or gain gate (`439–441`). `engine.start` executes before the UI (`1622–1624`). MMCSS is registered by the caller thread (`509`) instead of the audio callback thread and is never reverted. Startup should permit playback-only/monitor-off and register/revert scheduling on the actual worker where appropriate. This audit did not activate or measure monitoring.

## Browser edition: independently identified defects

These findings refer to the root installed HTML only; the internal HTML differs and needs its own selected-build mapping. They are not proof of native executable behavior.

1. **HIGH / VERIFIED static:** offline master rendering creates a vocal bus but never connects each `tPan` to it (`btnExportMix`, roughly 4926–5089; track loop 5058–5080). Vocal tracks are disconnected from exported output despite a success toast.
2. **HIGH / VERIFIED static:** takes, decoded buffers and telemetry exist only in in-memory arrays; localStorage contains the lyric blueprint only. There is no project/take persistence or browser-close recovery path (`takeObj`, 4555–4575). Do not confuse this with the native disk take folder.
3. **HIGH / VERIFIED static:** record pre-roll awaits before setting `isRecording` (`4003–4012`), allowing multiple starts; finalization uses shared chunk/telemetry arrays and the track armed at completion, so rapid starts or track changes can mix sessions or route the take incorrectly.
4. **HIGH / VERIFIED static:** recording from a nonzero `playbackOffset` stores no take timeline offset (`4037–4045`, `4555–4571`); stem playback/comping indexes from absolute song zero (`4728–4763`, `3056–3137`).
5. **MEDIUM / VERIFIED static:** recording loop calls `seekToTime` repeatedly after loop-end but seek updates playback only, not the recording clock (`4317` loop branch; `4825` seek function). Count-in and active recording need explicit cancellation/loop policy.
6. **MEDIUM / VERIFIED static:** stem splitting sends a filename without the selected file bytes, reports four stems on non-200/partial decode and reports fallback success on exception despite no fallback (`3205–3263`). ACE success accesses undefined `timecodeDuration` (`3298`), and error branches claim generated/connected status. Return actual job IDs, uploaded source tokens, completed artifact lists, and explicit failures.
7. **MEDIUM / VERIFIED static:** empty telemetry returns 75 scores (`4606–4609`); no onsets/pitches yields positive default values (`4625`, `4641`). Silence/insufficient coverage must remain unscored. Pitch accuracy needs a reference melody or clearly named scale-distance measure, and breath health cannot be inferred from these scores.
8. **MEDIUM / VERIFIED static:** an assumed 20 ms latency is destructively removed from every recording (`3420–3429`, `4531` onward), including when measurement is unavailable. Preserve raw capture and apply a reversible calibrated offset with device/sample-rate provenance.
9. **MEDIUM / VERIFIED static:** "autotune" only computes a snapped target/label (`4186–4219`); no corresponding pitch-shift DSP exists in that path. Mark monitor-only until implemented. Formant/HNR/breath labels and initialized plausible values overstate simple heuristics.
10. **MEDIUM / VERIFIED static:** top-level unguarded JSON.parse of saved blueprint (`2248`) can stop the script; editable cue values are interpolated into innerHTML (`2661`, `2685`, editor 5343+), allowing persistent markup/script injection in the local bridge origin. Render text, validate finite sorted timestamps and handle corrupt/quota storage.
11. **LOW / VERIFIED static:** PCM16 conversion condition `(0.5 + sample < 0 ? ... : ...)` in `bufferToWave` (`4874–4914`) tests -0.5 instead of zero, causing small signed quantization error. Prioritize capture loss before this one-LSB detail.

The initial hypothesis that the browser de-esser wrote an invalid negative GainNode value was rejected: it is a peaking BiquadFilter with valid decibel gain, not a GainNode. It must not be listed as a defect.

## Prioritized product expansion — PROPOSED, not completed

1. **Preserve every take and make the existing controls truthful.** First fix recording durability, output drain, export crashes, destination/timeline placement, silence states and ineffective controls. Acceptance: a synthetic five-minute take retains all samples; interrupted recording recovers; arm/solo/pan/export are consistent; no result is called successful without an artifact.
2. **One project model shared with AI-BS.** Add song metadata, tempo map, original source IDs, clip/take ranges, non-destructive comp decisions, cue revisions, device settings and plugin state. The standalone DAW can remain separately launchable while AI-BS opens the same project. Keep editable source separate from recovered binary distribution.
3. **A focused recording workflow.** Song selection → input/output check → optional measured calibration → lyric rehearsal → count-in/punch → take compare → comp → level/pan → export. Add undo and A/B before broad new tabs. Keep the raw recording untouched and explain unavailable capabilities in place.
4. **Evidence-backed coaching.** Analyze asynchronously; show pitch confidence/coverage, timing against actual beat/melody reference, loudness and clipping. Provide comparisons between the user's takes and adjustable practice sections. Treat physiological claims as unavailable unless independently validated; breath prompts can be authored cues rather than diagnoses.
5. **Cancellable creative jobs.** Upload/import media explicitly; queue stem/MIDI/backing generation with progress, cancellation, provenance, versioned output paths and reusable cache. Distinguish Demucs neural separation from simple spectral filtering, and generated output from cached/manual material. Keep offline recording independent of AI-server availability.
6. **Production-quality audio engine.** Short real-time callback, prepared DSP graph, analysis worker, safe plugin swapping and fault containment, sample-accurate automation/transport, loudness/true-peak reporting, offline/live parity and explicit dry/processed stems. Add render tests with impulse/sine/noise fixtures before purchasing or integrating further dependencies.

## Limits and next executable work

No device latency, microphone quality, audible result, AI model quality, driver stability or plugin compatibility was tested. Those require a controlled later session with the user's audio hardware. The immediate reproducible next step is to apply fixes in the new project source (preserving this exact source snapshot), promote the seven pure reproductions into meaningful regression checks, then package a separate review build. Do not launch the current binary merely to verify these already-proven static defects.
