# Staged native PC audio playback

This is a separately built, verified staging module. It has not been copied into
`C:/AI-BS`, installed in the canonical SDK, wired into First Boot or deployed.
Only synthetic PCM was played during its tests. Family speech was never played
by these tests. The main project and its build state were read-only.

## Public contract

`aibs/audio_playback.hpp` declares a noncopyable, nonmovable owner-thread
`AudioPlayback`. Construct, use and destroy it on the same game/window thread.
Construction allocates its small implementation but does not initialize audio.
The constructor can propagate allocation failure. Every subsequent operation is
`noexcept` and returns a bounded enum/native-code result; device absence does not
throw through the game. A wrong-thread operation returns `wrong_thread` without
reading or changing mutable owner state. Destruction on another thread violates
the owner-thread contract; the backend never uninitializes someone else's COM
apartment in that case.

```cpp
aibs::AudioPlayback memory;
memory.set_volume(0.7f);              // this object's source volume only
auto result = memory.play(asset);    // explicit playback; no automatic start
if (!result) { /* show bounded error/unavailable state */ }
memory.pause();
memory.resume();
const auto progress = memory.snapshot();
const double caption_time = progress.position_seconds();
memory.stop();                      // drain, release copy, reset clock to zero
memory.close();                     // drain and enter terminal closed state
```

`play(asset)` keeps the configured volume; `play(asset, volume)` explicitly
sets it for that clip. Volume is finite0..1. Pause/resume are idempotent in their
respective states and reject stopped/completed/failed states. Explicit Play is
needed to start a new stream after completion. Close is idempotent and terminal.
Natural end retains `played_frames==total_frames` for the caption clock, while
releasing the voice, private engine and owned PCM. Stop/Close clear duration and
position. `generation` increments only after a new clip successfully starts.

The supplied `AudioAsset` is fully validated, including its caption data, then
the entire interleaved PCM16LE byte vector is copied. No reference to caller
storage or asset metadata survives. Sample rate and channel count are passed
unchanged to the source voice and checked through `GetVoiceDetails`. A complete
44.1kHz stereo recording stays44.1kHz stereo in the imported asset, cooked payload
and source voice. This module does not crop, offline-resample or downmix it.
Windows/XAudio2 can still convert and route audio to the actual default output
device's mix format. That device conversion must not be confused with modifying
the retained recording.

Caption positions use the source voice's `SamplesPlayed` in frames divided by
the original source sample rate, not render delta time or individual interleaved
samples. The private engine's StopEngine/StartEngine preserves the real cursor
during Pause/Resume. No global engine, device volume, Windows sound setting,
endpoint selection or other application's audio is changed.

The caption review flag is not changed by playback. First Boot integration must
independently require checked captions before offering the intended original
memory playback, provide text from the matching source-frame intervals, and
keep authored new gameplay guidance distinct from the original recording.

## Ownership, errors and budgets

The active PCM **capacity** is charged in `owned_pcm_bytes` separately from the
immutable asset's decoded residency. It is not zero-copy. Active playback permits
at most48MiB of PCM; transactional replacement permits at most96MiB of simultaneous
old/new PCM capacity, with the observed high-water value in
`peak_owned_pcm_bytes`. Include this duplicate residency when admitting the
chapter's128MiB combined runtime budget; do not count only the cooked file sizes.
XAudio2's internal device/voice buffers are additional platform allocations and
are not misreported as application-owned PCM.

Replacement validates, copies and creates a stopped candidate first. Invalid
assets, allocation errors and unavailable candidate devices preserve the old
clip. The old playing engine is paused before starting a candidate. If starting
fails, the old playing device is resumed; an old paused clip stays paused. If
restoration itself fails, the module enters failed state and drains resources.
Errors are enums and numeric HRESULT values, with no private paths or unbounded
callback strings. An engine callback stores only an atomic critical error; the
next owner-thread snapshot converts it into failed state and releases resources.

Each clip declares its PCM member before its device member so device destruction
finishes first. The XAudio2 adapter stops its private engine, destroys the source
voice, destroys its mastering voice, unregisters the engine callback and releases
the engine before its retained callback object or PCM can be destroyed.
DestroyVoice is the documented completion fence for audio reads and callbacks.
No busy-wait callback loop, detached thread or source-file I/O is used. Native API
draining may briefly block; the test process is also externally bounded and
joined rather than relying on an indefinite wait.

## Files and integration

- Public: `include/aibs/audio_playback.hpp`.
- Implementation: `src/audio_playback.cpp`, `src/audio_xaudio2.cpp`.
- Private implementation/test seam: `src/audio_device.hpp`; keep this next to
  the implementation, not among installed public headers.
- Required public module: AudioAssets (`validate_audio_asset` and owned types).
- Windows private libraries: `xaudio2.lib`, `ole32.lib`; no new downloaded binary
  dependency. Tested with Windows SDK10.0.26100.0, MSVC19.44 and C++20.
- Synthetic tests: `tests/audio_playback_api_red.cpp`,
  `tests/audio_playback_tests.cpp`, `tests/audio_playback_device_tests.cpp`.

The staging CMake compiles the sibling `audio_pipeline` sources read-only and
imports the retained installed Core SDK. A canonical integration should instead
link the canonical AudioAssets target. Do not copy staging build directories or
absolute staging paths into the SDK. Root still owns canonical CMake, SDK export,
game controls, caption presentation and packaged acceptance.

## Verification

The actual first build failed with C1083 for the missing public header
(`missing-api-red.log`). After implementation, strict `/W4 /WX /permissive-`
Release and Debug each passed three isolated tests. Contract tests cover
caller-storage destruction, voice-before-PCM lifetime, rate/channel identity,
sample-frame caption timing, Pause/Resume, natural end, Stop/Close, invalid input,
wrong-thread operations, unavailable devices, volume/control failures and both
playing/paused replacement rollback. The private backend seam enables bounded
failure tests without touching a hardware endpoint; it is not a production
fallback or pretend device.

The actual device test uses all-zero synthetic PCM and per-source volume0. It
checks44.1kHz stereo playback, explicit controls, source-format replacement,
natural completion and destruction. A separate direct-adapter check reads the
actual XAudio2 SamplesPlayed before/after150ms of pause and confirms it resumes.
This establishes real device execution without playing private speech. It does
not establish audible loudness, speech intelligibility, caption accuracy, device
loss recovery on every driver, or complete gameplay integration.

An initial Debug invocation accidentally linked the Release-only SDK import and
failed with LNK2038. Diagnostics are preserved in `build-debug.log`; no compiler
or test assertion was weakened. Fresh `out-debug` uses the installed Debug SDK;
corrected Debug and final Release passed. `verification.json` binds exact staged
sources and the frozen sibling AudioAssets implementation used for those checks.

## Official API sources reviewed

- [Initialize XAudio2 and COM](https://learn.microsoft.com/en-us/windows/win32/xaudio2/how-to--initialize-xaudio2)
- [CreateMasteringVoice and default output](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2-createmasteringvoice)
- [CreateSourceVoice and source PCM formats](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2-createsourcevoice)
- [SubmitSourceBuffer data lifetime](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2sourcevoice-submitsourcebuffer)
- [GetState source cursor](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2sourcevoice-getstate)
- [SamplesPlayed semantics](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/ns-xaudio2-xaudio2_voice_state)
- [StopEngine preserves graph and cursor](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2-stopengine)
- [DestroyVoice completion/lifetime guarantee](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2voice-destroyvoice)
- [Unregister engine callbacks](https://learn.microsoft.com/en-us/windows/win32/api/xaudio2/nf-xaudio2-ixaudio2-unregisterforcallbacks)
