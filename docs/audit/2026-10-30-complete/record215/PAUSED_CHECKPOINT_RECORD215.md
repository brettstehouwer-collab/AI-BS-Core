# AI-BS Record215 — applied overlay checkpoint, paused

Status: APPLIED_READY_NEXT_BROADCAST_PAUSED_BY_USER. The user requested saving, applying completed work, and pausing. No additional chat/audio/bitrate development is authorized by this closeout.

## Applied and verified

- Native capture now supports a viewer-facing BGRA reaction compositor in the existing owned capture pipeline. The native v5.329.86 executable remains unchanged; its external Python coordinator loads this feature on the next Start broadcast. This is a backend update plus companion native controls, not a claim of a rebuilt Studio binary.
- Saved private settings: overlay enabled, local screen OCR enabled, viewer chat disabled. Open `C:\AI-BS\Live AI Overlay.lnk` for native controls. The hype button becomes available when the coordinator reports eligible game frames. No public broadcast was started or restarted by application of these settings.
- Initial English screen patterns: Fortnite victory, elimination, knockdown. Two high-confidence observations are required; reactions expire and have cooldowns. This does not establish detection of every game or every banner.
- Raw frames are sampled at most every 0.8 seconds on a CPU analysis worker. OCR sees the game before composition, so reactions cannot read themselves. Unknown/browser/screen-share frames do not trigger game events. Source changes and disabled settings clear old reactions.
- Hype captions are curated, not generative model outputs. The AI component is local OCR. No paid API, game input injection, microphone access, or OBS dependency was added.
- 109 focused tests and 64 subtests passed (173 XML cases, zero failures/errors). Coverage includes event confirmation, expiry, cooldowns, command filtering, source eligibility, teardown truthfulness, private IPC, preview, coordinator ownership and reboot recovery. This is not a claim that the full repository test suite passes.
- Offscreen native controls were rendered and visually inspected. Chat/poll controls are visibly unavailable. The offscreen Qt plugin initially lacked system fonts; the smoke harness explicitly loads installed Segoe UI fonts. The harness does not alter production settings.
- Thirty actual 1280x720 compositor renders averaged 3.659 ms, max 4.039 ms. This is a local frame-composition benchmark, not a measured live stream latency or a guarantee under game load.
- Local OCR smoke on the historical Fortnite lobby frame initialized and inferred in 2.063 seconds, reached `local_ai_ready`, and emitted no false game event. The included overlay image is clearly marked OFFLINE PREVIEW / EXAMPLE STUDIO HYPE EVENT, not a live event.

## Corrections and remaining limits

- Private IPC initially rejected the new settings with `IPC_PATH_UNEXPECTED`. Added a narrow filename allowlist for overlay configuration/status, UUID commands, and existing previous-boot recovery archives; original path, ACL, owner and size checks remain. Regression tests passed.
- Fixed shutdown reporting: the wrapper must not claim success while its analysis worker is still running. The failing test and corrected behavior are preserved.
- Installing RapidOCR 1.4.4 initially added CPU onnxruntime 1.31.1 alongside existing onnxruntime-gpu 1.29.0. Removed the overlapping CPU package and reinstalled the original GPU 1.29.0 package without dependency resolution. Verified original version and TensorRT/CUDA/CPU provider availability. No claim of byte-for-byte original dependency equivalence is made. Future RapidOCR installation in this GPU environment should preserve the existing ONNX runtime rather than adding the overlapping CPU wheel.
- Guest Twitch handshake failed with `WebSocketConnectionClosedException`; a proxy exclusion did not resolve it. Chat and polls remain disabled and are not presented as connected. No more connection retries during this checkpoint.
- End-to-end live screen-event recognition, overlay delivery to streaming platforms, performance during a match and authenticated viewer interaction remain UNVERIFIED. The observed coordinator is stopped; starting a public stream is left to the user.
- Record214 audio and per-platform bitrate drafts remain paused and unwired. Its failing engine-integration fixture is preserved. Audio/microphone changes and high-bitrate outputs were not applied by Record215.

## Preservation and resume

Live trading dispatch remains false. Crypto safety/control files and both ledgers match their recorded pre-change SHA-256 pins. No recruitment email dispatch, recordings, personal takes or original recovery backups were changed. Unrelated working-tree edits are excluded from this commit/package.

The package contains complete new source/tests, exact tracked diffs, relevant preimages, evidence and this report. It excludes environment files, exchange/stream keys, credentials, model/dependency caches and recordings. Cloud copies use only the existing AI-BS Complete Audit 2026-10-30 folder. Download-back verification is recorded separately after upload.

Next executable step, only after the user resumes: start a broadcast in Studio, open Live AI Overlay controls, verify actual game frames and use one manual hype burst. Then verify platform output. Chat integration and Record214 audio/bitrate work are separate incomplete tasks.
