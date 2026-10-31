# ComfyUI intent-routing repair — v5.329.79 / Records202–203

Updated 2026-10-31T16:18:12.099046+00:00. **Windows installed and Firebase web/mobile published v5.329.79.** The shared local backend is reloaded under trading/dispatch holds. Existing v5.329.78 windows were preserved and already use the corrected shared route.

## Reported defect and repair

The user screenshot showed `is comfy UI running?` being interpreted as an image-generation prompt. The prior classifier treated a ComfyUI service-name mention as creation authority. Status questions now return a bounded factual service observation before web search, coding, model selection or media dispatch. A status check performs at most two fixed loopback `/system_stats` GETs with a three-second total budget and64KiB response bound; it never starts a service, model or job. Unavailable/invalid responses are reported honestly, not replaced by readiness claims.

Current raw user input is carried separately in `user_prompt` across33web payload sites and the native transport. Formatted context, attachments and assistant history remain context rather than execution authority. Legacy clients retain prompt and last-current-user compatibility. Attachment-only review requests keep their existing safe review intent. Negated, quoted and informational messages do not dispatch media. Explicit image/video/3D creation remains supported and was verified with offline dispatch spies, not live generation.

API adapters retain their existing plain-text, chat JSON/content-SSE and OpenAI JSON/delta-SSE contracts. Eight adapter tests ensure service observations precede coding/history imports and selected-model/web work. Client plan/model choices cannot convert a status question into generation.

## Actual validation

-64client Node cases;10related native transport cases;16new policy/engine cases plus2selected safe existing media cases;8adapter cases and9actual-policy/endpoint composition checks pass. Cohorts overlap and are not added together.
- Canonical batch:191Python /75client tests, strictTypeScript and all16version paths pass. Its191Python includes synthetic paper/TWAP fixture output; no live trade was dispatched. The prior45native audit repair tests are accounted separately.
- Final live backend:7functional non-generating status/inquiry/negation cases pass, including the exact older-native screenshot payload, raw text overriding attached instructions, selected-model and plan-mode requests, and legacy JSON. `/v1/chat/completions` correctly rejects the local-admin credential at its commercial auth boundary(401); that alias is **AUTH_HELD**, not a functional live pass or an auth bypass. Its adapter is separately tested offline.
- The actual health answer was: **ComfyUI is offline or not reachable on the configured local ports. No generation was submitted, and no service/model was started.** This observation is time-bound, not a permanent service state.
- Firebase:1,127staged files, including143fresh compiled outputs,983preserved approved public artifacts and canonical version metadata. All compiled/version files plus12public samples pass preview and live byte-hash readback(156checks). This is static artifact validation; applicationJavaScript and everyphone workflow were not executed.
- Windows:66frozen native modules,2,256installed files /560,876,713bytes, PE5.329.79.0, executableSHA`78dae89174286a970e81a66fc8288c1911b43766d3f6e0bdcce4a01f43acfef6`. Frozen local-connection support and all three main launchers pass; old v78windows and artifacts remain intact. Executable remains **unsigned**; fullGUI acceptance is not claimed.

## Prior desktop audit continuity — Record202

The user stopped Computer Use with Escape and requested use of the PC. Desktop input remains paused; Record203 used no desktop automation. Before that stop, live v78inspection reproduced a blank simple-mode page. RealQt regression tests fixed missing scroll content and command-palette selection. Isolated tests also fixed sampler shutdown races, fabricated crypto prices/ACTIVE claims and ineffective pause labels, and fabricated SystemHealth history/hardware states. Health reads existing producer data withoutDDL/seeds, caps console history at2,000blocks, and uses a cooperative SQLite VM budget; it does not preempt arbitrary nativeIO. Process cleanup from the monitor is a labeled dry-run audit rather than an unconfirmed kill action.

The explicit fixture harness constructed all53canonical views and enumerated647buttons. It exercised73reviewed pure-local clicks and10nested tab selections with zeroQtcallback errors.481workflow buttons remain held,16disabled,38Qtinternal,5valid menu hosts,20stateful inputs,8unbound mixer toggles and6dead meeting controls. Those categories total647. Construction and static inventory are not an end-to-end functional pass.53canonical routes map across4hubs; the packaged66-module source has890control syntax sites/761connections/31nested-tab sites. Static counts and runtime instances are different scopes.

The six meeting and eight mixer controls, fabricated meeting/media-readiness displays, broader provider workflows, Chroma vector identity recovery and duplicate-route ownership remain open. No unfinished availability repair was silently shipped. The canonical video/meeting files still match the old reviewed source; this release prioritizes the explicit routing defect while retaining the completed45-test native fixes.

## Integrity, history and limits

Live trading remains **disabled**, crypto8007absent; payments/outreach/background holds remain active. Four protected execution/monetary hashes are unchanged. Existing private administrator custody was reused without exposing credentials, and stopped runtime SQLite/cache/journal state was encrypted before both controlled reloads. No production database was opened by regression tests. Synthetic test cleanup incidents and instrumentation false negatives are retained with corrections in restricted evidence rather than hidden as product failures or passes.

The native promotion inventory initially failed because a Windows directory allocation size changed0→4096 with identical inode/mtime. The E-only workflow now preserves regular-file size checks and strengthens exact directory membership validation;13regressions pass. Product/binary guards were not bypassed. Initial runtime-verifier assumptions about the selected `/api/chat`JSON envelope, commercial auth, and the wording `No media generation` were corrected against actual contracts and retained as diagnostics.

Nine ledger prefixes and prior checkpoint/index history are preserved. Exact preimages, patches, source/client mirrors, paused-audit records, tests, runtime/build/deployment proofs and recovery receipts are retained in the [same Drive folder](https://drive.google.com/drive/folders/1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k). Recovery keys remain outside repository/cloud. The native79recovery delta requires the authenticated Record201v78base; it is not a standalone full backup. Cloud download/decrypt/reconstruction outcomes are recorded separately after upload.

ADR-126: keep current user intent separate from context; treat service status as read-only observation and creation as explicit authority. Preserve client transport formats/auth boundaries and existing windows while releasing an independently identified v79build. Whole-system audit remains **PARTIAL / IN_PROGRESS**.
