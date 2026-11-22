# October7 Vocal Studio: audit, repair and recovery — Record212

Review date: October 31, 2026 (America/New_York). Canonical project: `C:\AI-BS`. This record covers the installed October7 package, recovered first-party source, installers, audio workflows, browser bridges and release process. Final build and verification receipts supplement this report in `record212`.

## Outcome and product direction

October7 is now included as a project folder in both AI-BS workspace files, at `C:\AI-BS\October7_VocalStudio_DAW`. The original `C:\Program Files\October7_VocalStudio_DAW` installation and original editable source in `C:\Users\footb\OneDrive\Desktop\carrytodex\VOICECOACHF` were preserved. Repairs apply to the project copy. Existing executable copies have not been overwritten.

The implemented code points to a **song-centered vocal rehearsal and production workstation**: backing arrangement → lyric/breath cues → layered vocal takes → comparison and comping → effects/mix → exports. This is an inference from the code, not a claim of a finished general-purpose DAW or scientifically validated vocal coach. The native application and older browser prototype implement different parts of that vision.

The original native source was proven compiled-code equivalent to `October7_VocalStudio_Native.exe` at Python optimization levels 0/1. It does not match the older `October7_VocalStudio_DAW.exe`. A source fix cannot repair either already-built executable; the new candidate is built separately and identified by its own manifest.

## Evidence, data preservation and limits

- Installed package: 10,591 files, 7,146,613,269 bytes (about 6.66 GiB). Recovered editable source: 23 files, 495,937 bytes. Python syntax, packaged entrypoints, dependencies and selected workflows were inspected locally.
- Before repairs, an independent recovery copy was placed at `C:\AI-BS-Recovery\October7_Audit212\pre_repair`. All 10,614 files / 7,147,109,206 bytes matched SHA-256 hashes against the project copy. The manifest is `C:\AI-BS-Recovery\October7_Audit212\recovery_manifest212.json`, SHA-256 `f45f0f696b15cb989c7e6129c67aa21da4c7e5cbbee24aa5e76329916c55fc19`.
- No original recording was decoded, edited, deleted or uploaded. No installer, uninstaller or machine-root certificate change was executed. Existing take and stem directories were preserved.
- Defects were reproduced with isolated temporary files, synthetic audio, extracted definitions and intercepted installer/compiler actions. Such tests establish specific contracts; they do not establish real device latency, microphone quality, VST compatibility or complete GUI workflow correctness.
- Native Qt is the actual interface; no WebEngine/Chromium runtime was found in the native package. Presence of unrelated modules in an archive is not evidence that they run.
- A bounded scan of the 23 recovered source files found no matches for the tested credential-literal/token patterns. That is not a guarantee that every binary, environment file or historical snapshot is secret-free.
- Live trading remained disabled. This task does not configure exchange keys or start the crypto daemon.

## Critical and high findings

No independently verified critical-severity exploit or tampering was established. The following high risks warranted immediate repairs or explicit holds. Original line references are preserved in the detailed reports and pre-repair diffs.

| Finding | Original behavior and consequence | Repair / disposition |
|---|---|---|
| N01: capture truncation | A ten-second ring was drained only after Stop; short writes were ignored. Twelve seconds retained about ten seconds and silently lost 96,001 samples. | Repaired source: dedicated writer drains the bounded queue continuously, checks accepted frames, and reports incomplete captures. |
| N03: early EOF | Producer prefetch reached the end and stopped transport before queued audio played. | Repaired source: consumer drains queued audio before stopping. |
| N04: WAV export failure | Both nonempty export paths referenced an undefined `HAS_SOUNDFILE` flag. | Repaired source: calls the actual library and does not report success on a failed write. |
| N07/N08: recording lane and timing | Recording overwrote Lead regardless of armed lane; a take recorded mid-song played from time zero. | Addressed by the second native repair batch; final receipt describes destination capture, clip offsets and retained take history. |
| N09: session loss | No durable project/session state or complete recovery workflow; take data and timeline state could be lost. | Second native batch adds versioned per-user session persistence and preserves raw takes. Complete power-loss recovery and a recovery UI remain limitations. |
| S01/S02: destructive installation | Source could equal destination; recursive replacement or uninstall could delete the program and recordings. | Repaired project installers reject overlapping trees and merge application files without deleting user media. Recursive uninstall is disabled pending a reviewed ownership manifest. |
| S03: machine trust changes | Installer imported a self-signed public certificate into the machine Root store without an expected fingerprint check. | Root imports removed. Optional certificate review does not change trust. Existing signatures were Valid on the audited machine; that is not a blanket SmartScreen or hardware guarantee. |
| S08/S09: Python legacy bridge | All-interface binding, unconfined paths, wildcard CORS, unauthenticated hardware/state actions, no request-size limits. An extracted GET handler read a harmless fixture outside the intended directory. | Hardened source and isolated boundary tests are recorded separately. This bridge is not part of the native entrypoint. |
| S11: Node static bridge | All-interface binding and `startsWith(root)` containment accepted adjacent paths with the same prefix. | Hardened source and offline path/HTTP tests are recorded separately. |
| Browser export | Vocal source/gain/panner graph never connected to the vocal bus, yet export reported success. | Repaired source graph; a test checks that an active vocal reaches the output destination. |
| Browser state/record concurrency | Takes exist only in memory, count-in can race, and clips lack a reliable song-time origin. | Still open in the legacy browser edition. Native fixes do not establish browser persistence or recording correctness. |
| Build identity and broad package | Different scripts selected different applications; a 13,653-module native archive contained unrelated AI-BS/backend/finance libraries. | Canonical native build and isolated dependency environment; versioned candidate and package checks provide release identity. |

## Medium and low findings

| Area | Verified finding | Current disposition |
|---|---|---|
| Native mix | Pan and solo behavior differed or was ignored between playback and export. | Shared mixing path repaired and tested. |
| Native finalization | Same-second filenames collided; failed writes could replace a track or claim success. | Unique names, explicit failure state and retained prior takes. Pending unwritten samples can still be lost if the process or machine fails. |
| Native analysis | The pitch/HNR window cannot support its configured lag range; example notes and coaching scores masqueraded as measurements. | Native labels changed to unavailable when unmeasured. A real rolling-window analyzer remains roadmap work. |
| Native controls | EQ/compressor/reverb/air and cue-editor controls do not all implement the described function. | Explicitly open; do not call all controls functional. |
| Native concurrency | Mutable track/ring state crosses GUI, producer and callback threads; seeking and plugin operations need stronger ownership boundaries. | Partially reduced by capture/session work; full real-time command-queue redesign and timing tests remain open. |
| Native transport/import | Loop/UI cursor divergence, GUI-blocking imports, possible duplicate arrangement inputs and inflexible sample-rate behavior. | Open unless an individual final receipt explicitly records a repair. |
| Native startup | Automatic elevation and eager audio-device opening produced unnecessary side effects and poor failure recovery. | Second native batch removes automatic elevation/device activation and provides explicit device enablement. No microphone/device was opened by this audit. |
| Installer | Optional shortcut variables were undefined; apostrophes broke generated PowerShell; subprocess failures were ignored. | Repaired and reproduced with harmless temporary fixtures. Tk worker-thread UI updates remain an architectural follow-up. |
| Browser startup | A missing brace before `catch` in `pollAiHeartbeat` prevented the embedded script from parsing. | Repaired; every embedded script parses without executing the page. |
| Browser text | Saved lyrics/sections were interpolated into HTML/attributes, including comping labels. Malformed localStorage could abort startup. | Escaping and shape-checked recovery preserve damaged storage without overwriting it. Rendering tests include hostile text fixtures. |
| Browser heartbeat | Unbounded fetch and unsupported claims of an active/generated fallback. | Five-second abort and capped retry spacing; unavailable means unavailable. No model/provider service was patched. |
| Browser AI jobs | Stem splitting and generation can claim success without completed artifacts; scoring contains example fallback values. | Still open. Treat as unverified, not generated or measured output. |
| Release/install verification | Missing demo-resource declaration, non-atomic overlay deploy, ignored signing failures, absent version metadata and unsupported latency/readiness claims. | New candidate gains a version and manifest; complete signed/staged deployment acceptance remains distinct from an offline build. |

The detailed audio review contains 21 native and 11 browser entries; security/installer review contains 12; package review contains 6. Some overlap. Counts are coverage records, not a claim of 50 independent vulnerabilities or a review of every third-party source line.

## Remediation and verification

The first repair batch passed 33 focused offline tests. An independent reviewer repeated the 14 native tests and inspected writer lifetime, EOF and mixing. The final combined October7/core/broadcast run passed **131 tests and 18 subtests in 9.82 seconds**; the separate browser suite passed **seven checks**. Later receipts supersede initial hashes. The exact source patch, per-file SHA-256 manifest and build identity are in the evidence directory.

The separately staged candidate is `C:\AI-BS\releases\october7\native-1.0.212.0\October7_VocalStudio_Native\October7_VocalStudio_Native.exe`, SHA-256 `fa212891edcc3046eec30e7c4ded1fa9058cf21ede6b92f9ee1a3a0e57c7d288`. Building took 64.093 seconds. Static inspection verified source-bytecode equivalence, Windows AMD64/version 1.0.212.0/asInvoker resources, required native audio/Qt files, and absence of the tested unrelated module families. The bundle contains 447 files / 253,289,681 bytes and 1,110 Python archive modules. It is unsigned and was not launched against devices. The original 7.1 GB installation also includes a separate legacy application and media, so the two directory sizes are not a like-for-like application benchmark.

The browser suite now covers JSON/storage recovery, cue and comping text safety, vocals reaching the export output, whole-script parsing and heartbeat failure states. Original failures and passing results are retained. Tests never run an installer or rely on personal audio.

Run focused verification from `C:\AI-BS` using the exact commands in the final verification receipt. Native/build/installer tests use pytest; browser/server JavaScript uses Node's test runner. The release candidate is checked statically against the final repaired source. Device/GUI tests are deferred rather than reported as passed.

## Practical improvement roadmap

1. **Reliable sessions first.** Keep immutable raw takes, session metadata and clip song offsets outside installation directories. Make autosave, undo/redo, recovery choice and interrupted-write handling visible. Never overwrite the only copy of a performance.
2. **One native product and one release pipeline.** Keep the older browser tools separate. Use an isolated, pinned environment, explicit resources, a versioned release directory, dependency inventory and source/artifact hashes. Test a clean install before promotion.
3. **Measured coaching.** Analyze a longer rolling window outside the callback; report voiced confidence and unavailable states. Add pitch contour, timing against lyric cues and reference A/B. Avoid medical or objective-quality claims from example scores.
4. **Nondestructive vocal workflow.** Add lane-based comping, take audition, clip placement/trim/fades, latency compensation and sample-accurate transport. Connect cue edits and effects only when their behavior has tests and persists across reloads.
5. **Useful mastering and delivery.** Add loudness/true-peak measurements, dry/processed stem exports and live/offline parity checks. Send completed, versioned artifacts into AI-BS Broadcast Studio through an explicit handoff.
6. **Optional AI as jobs.** Upload/identify the actual source, create a durable job ID, show progress/cancel, and surface failures. Only claim completion after validated output artifacts exist. Keep heavy AI dependencies out of the real-time audio process.

## Bad Request incident and usage-review evidence

The recurring `{"detail":"Bad Request"}` was observed in the chat/tool workflow. Its exact originating service, request ID and rejected payload were not available here. Oversized context or malformed tool payload is plausible but unconfirmed. No claim is made that OpenAI billing, a model API or the remote backend was repaired.

This audit limits requests to specific modules, processes the multi-gigabyte directory on disk, keeps raw binaries/media out of model context, writes long logs locally, and returns bounded summaries. Failed Drive operations were not retried indefinitely. These measures reduce avoidable request size and repeated failures; they do not prove the original cause.

Only recorded operation times are authoritative: copy/recovery timestamps, test durations and build start/end receipts. They are not a billable-usage calculation. A complete earlier wall-time total, token utilization, refund eligibility or account usage adjustment cannot be established from these local records. Keep the existing screenshots and this record for a usage-review request.

## Record location and external state

All records for this batch are saved locally under `C:\AI-BS\docs\audit\2026-10-30-complete\record212`, with raw working evidence under `C:\AI-BS\backups\october7_audit212`. The independent recovery tree remains outside the project.

Google Drive writes returned 403 permission errors. The user then explicitly instructed **save locally for now** because the subscription could not be renewed. No upload is claimed. Future uploads must use the existing single folder `1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k` (AI-BS Complete Audit 2026-10-30); no alternate cloud folder was created.

The authoritative final candidate path, completed checks, modified paths, open findings and next acceptance step are recorded in `OCTOBER7_VOCAL_STUDIO_AUDIT_RECORD212.json` and the agent-sync handoff. Original installed binaries retain their original behavior until deliberately replaced by a verified release.
