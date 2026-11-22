# Record209 — Native program preview and broadcast retirement, v5.329.85

The native broadcast workspace now includes read-only delayed program-video playback from the existing HLS output through one Qt media player/video sink. Decoded images are copied into the canvas. At acceptance the game was intentionally closed, so the installed GUI correctly held a blank canvas. The separate HTTP decoder probe verifies playback capability; actual 85 live-game rendering was not performed. Preview creates no second game/desktop capture, no audio-output object and no start/stop/source dispatch.

The 84candidate initially showed real preview and its off/on control preserved the same encoder. Later, controller 52852/encoder 43860 failed with STATUS_WRITE_UNAVAILABLE; root sent no Stop. Windows fixture reproduction confirmed that ordinary file readers could deny atomic replacement, while local playlist playback also produced rename failures. This is a recorded incident; the prior 346-case suite did not detect the Windows sharing defect. The corrective 85 release and restored runtime are distinct later states.

## Repairs and preservation

- Fresh private coordinator ownership, process creation epochs, encoder progress, bounded manifest admission and three-second state TTL gate preview. Changed source/session, stale output and failed decoder clear buffered images. Retries and cleanup are bounded.
- Corrective 85 reads IPC/HLS with FILE_SHARE_DELETE, retries only classified Windows replacement sharing/access errors within a fixed bound, and moves Qt playback to fixed loopback HTTP 9011. It does not convert an exhausted publication failure into success.
- Current native/web OBS buttons, labels, active 4455 probes, executive process placeholders and fake/proposed Lexicon scene automation are retired. The native executive directs operators to Native Broadcast Studio and does not infer stream health from a listening port.
- Shared-memory V1 keeps all 25 original numerical bit positions, including the reserved 4455 slot. Active probes and HUD render 24 ports under their original mask tags; no stored data or SHM version was deleted.
- Browser capture/audio/OAuth settings remain app-owned local web drafts. Existing stream/stop/panic and Lexicon lookup handler bodies are preserved. Four canonical/mirror trees match exactly; the standalone app received narrow compatible edits. Omni imports now resolve through actual canonical /src paths.

## Verification

| Check | Actual result |
|---|---|
| Final guarded native cohort | 352 tests, 28 groups; zero failures/errors/operational guard denials |
| Focused web checks | 35 tests pass; zero failures |
| Frontend TypeScript | exit 0 |
| Native version mirrors | 16 mirrors, v5.329.85 |

Reproducible guarded command from the repository root: `C:/AI-BS/pyppeteer_env/Scripts/python.exe -B scripts/verify_native_broadcast_offline.py`. The versioned runner matches the tested corrective runner byte for byte; the equality check does not rerun the suite.

Focused native subsets are included within the final native count and are not added again. The pinned Windows asyncio self-pipe allowance is separate from operational network permission. Actual Windows sharing fixtures and the installed-app media checks below are identified separately from effect-denying unit tests. The original 84 Qt prototype decoded 145 distinct 1280×720frames in 5.328seconds, with no audio output; it is retained as pre-failure historical evidence.

The first 352-case corrective run had five errors/guard denials because the physical C test-fixture mkdir path was outside the initial allowlist. That run is retained as failed harness verification. Only the exact fixture path was added; the separate clean 352-case run passed with zero denials and operational effects still blocked. This did not bypass a product assertion or permit live IPC/media actions.

The fixed HTTP 9011route was independently admitted as loopback-only: playlist GET 200, POST 403, and unrelated/tmp/private paths 404. That route check did not certify fresh/live video by itself.

The sharing fixture on this host still denied immediate replacement while the read handle remained open; bounded retry published after the brief reader closed. A permanently held reader can still exhaust the retry bound. No universal open-handle rename guarantee is claimed.

## Build, installation and actual acceptance

**Build**

```json
{
  "receipt": "backups/native_preview_v85_20261031_record209/build_verification/build_independent_verification209.json",
  "result": {
    "status": "VERIFIED_WINDOWS_V85_PE_PYZ_FROZEN_INPUTS_PACKAGE_BOUNDARY",
    "utc": "2026-10-31T20:32:37.361238+00:00",
    "exe": "backups\\native_preview_v85_20261031_record209\\stage1\\dist\\AI_BS_Studio\\AI_BS_Studio.exe",
    "exeSha256": "26db181ca8414de555f31ec0010acf51bb35a679d042bd50a72f03e82d0fb34c",
    "fileVersion": "5.329.85.0",
    "packageFiles": 2256,
    "packageBytes": 552599001,
    "frozenInputCount": 82,
    "frozenInputsAllUnchanged": true,
    "canonicalMappingCounts": {
      "canonical_native_or_version": 72,
      "canonical_frontend_public_asset": 2,
      "retained_v81_distribution_metadata": 7,
      "generated_native_build_metadata": 1
    },
    "allNativeModulesCompiledSourceEquivalent": 71,
    "requiredHelpers": {
      "native_studio.broadcast_ipc": {
        "compiledSourceEquivalent": true,
        "matchingOptimizationLevels": [
          0,
          1
        ]
      },
      "native_studio.broadcast_preview": {
        "compiledSourceEquivalent": true,
        "matchingOptimizationLevels": [
          0,
          1
        ]
      },
      "native_studio.broadcast_secondary_control": {
        "compiledSourceEquivalent": true,
        "matchingOptimizationLevels": [
          0,
          1
        ]
      }
    },
    "backendModuleCount": 0,
    "sensitiveRuntimeFilenameMatches": [],
    "sensitiveDataScope": "Filename/data-boundary check plus previously recorded prebuild source-key scan; no live credential values read or printed",
    "applicationExecuted": false,
    "desktopOrCursorControl": false,
    "runtimeChanges": false,
    "fullGuiCertification": false,
    "knownLimits": [
      "Explicit screen sharing held/unsupported",
      "Audio generated silence only"
    ]
  },
  "build_start_utc": "2026-10-31T20:29:47.722Z",
  "build_end_utc": "2026-10-31T20:32:17.543Z",
  "duration_seconds": 149.821
}
```

**Installation**

```json
{
  "receipt": "backups/native_preview_v85_20261031_record209/installation209.json",
  "result": {
    "status": "VERIFIED_WINDOWS_V85_INSTALLED",
    "utc": "2026-10-31T20:32:48Z",
    "exe": "C:\\AI-BS\\native_studio\\releases\\v5.329.85\\AI_BS_Studio\\AI_BS_Studio.exe",
    "exe_sha256": "26db181ca8414de555f31ec0010acf51bb35a679d042bd50a72f03e82d0fb34c",
    "file_version": "5.329.85.0",
    "package_files": 2256,
    "package_bytes": 552599001,
    "all_package_bytes_match_stage": true,
    "new_release_acl": "CurrentUser and SYSTEM only; old releases unchanged",
    "shortcuts": [
      {
        "path": "C:\\Users\\footb\\Desktop\\AI-BS Sovereign Studio.lnk",
        "before": {
          "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.84\\AI_BS_Studio\\AI_BS_Studio.exe",
          "arguments": ""
        },
        "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.85\\AI_BS_Studio\\AI_BS_Studio.exe",
        "preimage_sha256": "2627e2471d78fc11771fde707680f2f6a5d6ce07232802635fdce47c51eabf5b",
        "after_sha256": "986b93760cef89e323b6344dc9a41afe0fb7c45b021ae97d674e17ade976137d"
      },
      {
        "path": "C:\\Users\\footb\\Desktop\\AI-BS Executive Studio.lnk",
        "before": {
          "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.84\\AI_BS_Studio\\AI_BS_Studio.exe",
          "arguments": ""
        },
        "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.85\\AI_BS_Studio\\AI_BS_Studio.exe",
        "preimage_sha256": "b01d85018168bfc08bb78fdb1daa9ba421714f40899bd2b2fcbf7be8dccc39fb",
        "after_sha256": "fb4ffe3b43bf22e4cc759f71d078cfaa0ec6c459053f391cea6b86d0c750389b"
      },
      {
        "path": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\AI-BS Sovereign Studio.lnk",
        "before": {
          "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.84\\AI_BS_Studio\\AI_BS_Studio.exe",
          "arguments": ""
        },
        "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.85\\AI_BS_Studio\\AI_BS_Studio.exe",
        "preimage_sha256": "37294810ad006c96bfafb68e91f5577c72802739dc19b70a0892838f28a5ee12",
        "after_sha256": "7241167900ad5d48ca87584ec0c1ec3b0d240eeb1833974223818e3a20e284ba"
      },
      {
        "path": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\AI-BS Sovereign Studio\\AI-BS Sovereign Studio.lnk",
        "before": {
          "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.84\\AI_BS_Studio\\AI_BS_Studio.exe",
          "arguments": ""
        },
        "target": "C:\\AI-BS\\native_studio\\releases\\v5.329.85\\AI_BS_Studio\\AI_BS_Studio.exe",
        "preimage_sha256": "18c7162ad3c22f2c2adabe0d1440532bc2066d2991c63f2575e7cb2d3d5f953e",
        "after_sha256": "940d8141cbd25150fa596879208fd4cacc0a49ead88e2e8664d6152cc38178a7"
      }
    ],
    "running_stream_action": "NONE",
    "audio_capture": "DISABLED",
    "microphone_capture": "DISABLED",
    "live_trading": "DISABLED"
  }
}
```

**Installed native preview**

```json
{
  "basis": "PARENT_DIRECT_GUI_OBSERVATION",
  "version": "5.329.85",
  "reopen_maximize_navigation": "VERIFIED",
  "earlier_control": "Program preview checked; Preview: held; canvas correctly blank with no verified game",
  "latest_before_toggle": {
    "utc": "2026-10-31T20:43:37.296788+00:00",
    "preview_phase": "root-reported OFF, before ON confirmation",
    "status": {
      "status": "running_unverified",
      "active": true,
      "controller_pid": 36868,
      "controller_create_time": 1793478612.624772,
      "encoder_pid": 31084,
      "encoder_create_time": 1793478613.372554,
      "capture_state": "holding",
      "game_frame_verified": false,
      "holding_reason": "NO_VERIFIED_GAME",
      "source_mode": "auto_game",
      "frames_encoded": 24003,
      "out_time_us": 800100000,
      "audio_mode": "generated_silence"
    },
    "port8007_listeners": 0,
    "obs_process_count": 0
  },
  "latest_after_toggle": null,
  "final_preview_ON": "NOT_CONFIRMED",
  "actual85_live_game_render": "NOT_PERFORMED_USER_INTENTIONALLY_CLOSED_GAME",
  "independent_HTTP_decode": {
    "receipt": "backups/native_preview_v85_20261031_record209/runtime/http_qt_probe/receipt.json",
    "frames": 200,
    "seconds": 7.25,
    "size": [
      1280,
      720
    ],
    "timestamps_advance": true,
    "distinct_first_last_images": false,
    "holding_black_expected": true,
    "audio_output": false,
    "actual_GUI_render_tested": false
  },
  "last_observed_checkbox": "OFF",
  "final_ON_attempt": "BLOCKED_TWICE_BY_CONCURRENT_USER_INPUT_GUARD_ROOT_STOPPED_INPUTS",
  "parent_message": "user input was detected in this window; call get_window_state before continuing",
  "user_source_drafts": "Visible user edits were not applied or assumed accepted.",
  "gui_evidence": [
    {
      "path": "backups/native_preview_v85_20261031_record209/gui/preview_held.png",
      "sha256": "601bf69888664f5544676fbbdf98de2b3a16fd5575a1ee4e5a9961fd694942a3",
      "bytes": 351794,
      "approved_visual_no_credentials": true,
      "version": "5.329.85"
    },
    {
      "path": "backups/native_preview_v85_20261031_record209/gui/preview_off.png",
      "sha256": "b48d6897d63f9b8f2896ac78d94e5104b5bb472c935d3b6b45545c3bd0da11be",
      "bytes": 351235,
      "approved_visual_no_credentials": true,
      "version": "5.329.85"
    }
  ]
}
```

**Corrective sharing/HTTP proof**

```json
{
  "sharing_completion": "backups/native_broadcast_preview209_work/ipc_hotfix209/completion.json",
  "route_receipt": "backups/native_preview_v85_20261031_record209/loopback_http_route209.json",
  "first_restored_soak": {
    "receipt": "backups/native_preview_v85_20261031_record209/runtime/20261031T203059Z/soak.json",
    "start_utc": "2026-10-31T20:30:59.216459+00:00",
    "end_utc": "2026-10-31T20:34:11.286589+00:00",
    "seconds": 192.156,
    "controller_pid": 36868,
    "encoder_pid": 31084,
    "frames": [
      1240,
      6999
    ],
    "hls_sequences": [
      15,
      111
    ],
    "new_errors": 0,
    "same_pipeline": true,
    "preview85HTTPactivated": false
  },
  "final_runtime_receipt": "backups/native_preview_v85_20261031_record209/runtime/final_runtime209.json",
  "all_four_crypto_pins_match": true,
  "long_reader_limit": "Immediate rename while shared reader remains open is not universally supported on this host; retry succeeds after brief reader closes, exhausted bound still fails."
}
```

## Operational boundaries and recovery

Audio remains intentionally silent. No microphone capture, audio routing, game-source reconfiguration or additional game capture is part of preview. Live trading and external recruitment dispatch remain disabled. Actual restoration/continuity facts are qualified in the acceptance receipts; no uninterrupted-broadcast claim is made.

No Firebase deployment occurred this turn. Source/mirror parity does not certify deployed hosting. Remote RTMP dashboard acceptance, all games and every workflow remain unverified. Shared local source ACL/replacement TOCTOU and machine trust remain open; the preview changes do not establish a cross-user security boundary.

Exact C-backed preimages, full source/document copies and patches are retained. Encrypted full-source/binary cloud recovery remains blocked by existing unreadable E-key custody. No repeated E access, replacement key or plaintext recovery upload is claimed. Root handles sanitized uploads only in existing Google Drive folder 1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k.

Base commit: `f53527c0440d5e7255ba257ebf86c5315b7a440c`; branch `codex/audit-v532976-20261031`. The resulting source commit is resolved through `docs/agent_sync/manifest_record209_v532985.json` and root close receipts. The JSON companion retains exact evidence references and 84 candidate/failure history.

The separate `INCIDENT_AND_USAGE_REVIEW_RECORD209.md`/JSON documents user-requested support facts and elapsed windows. Its account-wide limits snapshot is not task cost, and its observed computer-use/window-loss symptoms are not a confirmed platform outage. No support submission or refund promise was made.


## Final observed controls and acceptance

Acceptance classification: **VERIFIED_INSTALLED_PREVIEW_CAPABILITY_HTTP_DECODER_AND_SAFE_HELD_GUI_LIVE_GAME_UNVERIFIED**. The installed v85 GUI initially showed Program preview checked, Preview: held and a correctly blank canvas because the user intentionally closed the game. Root then clicked preview OFF and recorded that state. Two final ON attempts were blocked by the tool’s concurrent-user-input guard (`user input was detected in this window; call get_window_state before continuing`); root stopped inputs. **OFF is the last observed checkbox state.** The user was advised to enable Program preview manually. Visible source draft edits were not applied or treated as an accepted coordinator source.

The independent HTTP probe decoded 200 black holding frames over 7.25 seconds without errors or audio output. It proves decoder capability, not v85 live-game GUI rendering. Final ON/after-toggle remains unconfirmed. No game or broadcast restart was performed for final acceptance. The reviewed held/OFF images contain no keys and are included only in the sanitized evidence package. No OpenAI backend outage is established.


### Final user constraint and read-only state

No more screen/cursor control or GUI retries are authorized. Root stopped all computer-use input; remaining work is backend/frontend code, offline tests and read-only checks. At 20:50:17 UTC the same controller 36868/encoder 31084 remained active in NO_VERIFIED_GAME holding, advanced to 36009 frames/media 1200.3 seconds, preview last observed OFF. The later read-only sample is not a completed ON toggle. Port 8007 listeners 0, OBS processes 0, all four crypto/ledger hashes unchanged. No game, source-apply or start/stop command was sent.


### Final credential-default cleanup and verification

Two pre-existing hardcoded Twitch/Facebook stream-key defaults in the standalone broadcast component were replaced with empty strings. Exact AST reconstruction verifies only those two literal substitutions; saved settings and handlers are unchanged. The count-only RED found 2 credential-family literals; final broader JavaScript bundle passed 35 tests (contracts198 + truth204 + debranding209), TypeScript exit 0. The narrower 33-case bundle is included, not an extra run. Native 352/28 groups and the installed 85 package are unchanged. No credential rotation, historical exposure conclusion or clean-Git-history claim. Original source, private preimages and raw patches stay C-only and are never uploaded.
