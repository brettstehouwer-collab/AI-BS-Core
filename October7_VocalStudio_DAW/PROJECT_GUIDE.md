# October7 Vocal Studio project

This folder is the preserved project copy of `C:\Program Files\October7_VocalStudio_DAW`, with recovered editable source and a first batch of verified source repairs. It is included in both AI-BS workspace files. The original installation and original OneDrive source were not changed.

## What you were building

The code points to a song-centered vocal production workstation: load a backing arrangement, rehearse with timed lyric and breath cues, record lead/doubles/harmony, compare takes, apply effects, mix and export. That is a useful product direction. It does not yet implement every function its controls describe.

There are two distinct applications here:

- `source/app_native.py`: the current native Qt/sounddevice/Pedalboard application. Its original compiled code matches `October7_VocalStudio_Native.exe`.
- `VOICECOACH PROGRAM.html`, `source/october7_core.py` and `source/server.js`: an older browser application and bridges. They have separate behavior and security findings. The old `October7_VocalStudio_DAW.exe` does not match the recovered native source.

The executable files copied into this folder are historical artifacts. **They have not been rebuilt with the repaired source.** Their original audio, export and elevation behavior still applies.

The repaired native candidate is now built separately: `C:\AI-BS\releases\october7\native-1.0.212.0\October7_VocalStudio_Native\October7_VocalStudio_Native.exe`. Its frozen entrypoint matches the final repaired source (SHA-256 `a7af7f4a81a593a12438ace9bb6a94e2f6af869ce7427df3f979ef0eebd75386`). It runs as the current user, with audio disabled until you choose Audio Devices and Enable. It is not signed or device-tested. No prior installation was replaced.

New sessions and takes live under `%LOCALAPPDATA%\October7VocalStudio`, outside the application directory. Existing recordings in the original installation and independent recovery tree remain intact; the candidate does not silently migrate or overwrite them. Use its audio import control to select existing media.

## Preserve your work

Independent pre-repair recovery copy: `C:\AI-BS-Recovery\October7_Audit212\pre_repair`.

Its manifest is `C:\AI-BS-Recovery\October7_Audit212\recovery_manifest212.json`. All 10,614 files were checked against the working copy before repairs. This backup sits outside the installed and project directories. No installer or uninstaller was run.

Keep recordings and session data separate from application releases. The project installers now reject overlapping paths, preserve existing takes and media, avoid importing machine-root certificates, and do not auto-launch. The uninstaller deliberately refuses recursive deletion; a proper ownership-based uninstaller remains future work.

## First repair batch

The native source now continuously writes captures outside the audio callback, reports incomplete recordings, preserves prior takes on write failure, drains playback before stopping at EOF, exports WAV without the undefined capability flag, and shares pan/solo/mute rules between playback and export. Take filenames are unique.

The build helper now targets `October7_VocalStudio_Native.spec` and `app_native.py`. It no longer builds the legacy server or invokes signing implicitly. `source/Launch Studio.bat` remains a legacy launcher and is not the native build entrypoint.

Focused offline verification from `C:\AI-BS`:

```powershell
python -B -m pytest scripts/tests/test_october7_native212.py scripts/tests/test_october7_installer212.py scripts/tests/test_october7_build212.py -q --disable-warnings
```

Initial result: 33 passed. After the second repair batch, the final combined October7/core/broadcast suite passed 131 tests and 18 subtests; the separate browser suite passed seven checks. Tests use generated samples, temporary directories and intercepted installer/compiler actions. They do not open microphones or establish real-time performance.

For later builds, use an isolated Python 3.12 environment and the exact pins in `source/requirements-native.lock.txt`; the companion hashes file pins the downloaded Windows wheels. The verified build used a separate environment under `C:\AI-BS-Recovery\October7_Audit212\native_build_1.0.212.0`, with system packages disabled. Inspect `source/October7_VocalStudio_Native.spec`, then run `python build_windows_app.py` from `C:\AI-BS\October7_VocalStudio_DAW\source` in that environment. Expected standard output: `source\dist\October7_VocalStudio_Native\October7_VocalStudio_Native.exe`. This batch's separately staged release is the candidate linked above. Signature handling, clean-install acceptance and explicit audio-device testing remain separate steps before replacing the installed program.

## Best next steps

1. Expand the new atomic session/history and raw-take preservation into a visible recovery workflow and undo before adding more processing.
2. Verify the repaired armed-lane routing and clip offsets on actual hardware; expand into nondestructive comping.
3. Replace example coaching scores with measured pitch/timing/confidence or a clear unavailable state. Analyze a rolling window outside the audio callback.
4. Connect or clearly disable unfinished cue and effects controls.
5. Build one reproducible native release from a small, pinned environment. Keep legacy servers separate until their file access and request boundaries are repaired.
6. Validate the new explicit device selection and recoverable audio errors on the intended interface. Automatic elevation and microphone opening at startup have been removed.
7. Expand with nondestructive comping, reference A/B, loudness-aware exports, lyric alignment and optional AI jobs with progress/cancel/retry controls. Connect completed mixes to AI-BS Broadcast Studio only through a tested handoff.

Full findings, original line references, exact repair patches and limits are in `C:\AI-BS\docs\audit\2026-10-30-complete\OCTOBER7_VOCAL_STUDIO_AUDIT_RECORD212.md` and its `record212` evidence directory. Live trading remains disabled and is unrelated to this audio project.
