# Record210 — Program preview controls, v5.329.86

The prominent toolbar button now controls the same real Program preview flag as its checkbox. It previously toggled cosmetic A/B state without enabling the decoder. Explicit OFF survives status polling; the canvas clearly distinguishes off, held, buffering and stale states. Capture, source selection and broadcast dispatch are unchanged by this UI repair.

The renderer/core source is unchanged. A stopped coordinator correctly held without decoding. After root’s one fresh Start, the eligible core accepted 73 images from 222 Qt frames over 8.453 seconds, with no error or audio output; actual v85 GUI video then appeared. The earlier unavailable state was transient warmup, not a reproduced persistent decoder/network defect. No GPU/backend workaround was added.

## Verification and release

| Check | Result |
|---|---|
| Full guarded suite | 356 tests/29 groups; zero failures/errors/effect denials |
| Focused UI checks | 15 passed, included in the full cohort |
| Version mirrors | 16 agree on v5.329.86 |
| Build/install | Build exit 0 in 120.668 seconds; 2256 files installed, 71 native modules verified |
| Actual installed GUI | Actual Fortnite image visible; toolbar OFF synchronized both controls, checkbox ON restored both and the picture; left ON |
| Runtime | Same 51964/51940 capturing after upgrade; 15224 frames, HLS 247; four crypto pins unchanged, port 8007 absent/OBS 0 |

Source/build/install/runtime hashes and exact receipts are in the JSON companion. Prior Record209 JavaScript checks are historical and are not added to this record’s native count. Build time: 120.667513 seconds; measured active model time and task cost remain unavailable.

## Findings, limits and continuity

User-pasted `{"detail":"Bad Request"}` is an unattributed message with 400-style wording: no URL, tool context or HTTP status was provided. It does not establish a preview HTTP fault or OpenAI outage. Fixed 9011 playback succeeded in the eligible state.

The user explicitly allowed PC control around 21:12 UTC, superseding the earlier prohibition. Only root performed bounded GUI actions; this record agent performed none. Live trading remains disabled; audio is generated silence with no microphone change. No all-games/workflow or remote platform acceptance is inferred, and no Firebase deployment/hosting-parity claim is made.

Record209 and prior release history are retained. Exact C preimages, source snapshots and diffs support recovery. Encrypted full-source/binary cloud recovery remains blocked by existing E-key custody, without E retries or replacement keys. Root handles sanitized uploads only in the existing single Drive folder. Base commit: `1c5b058acacf387198c72ed397e13e2110dfcff3`; final source commit reference: `docs/agent_sync/manifest_record210_v532986.json`.
