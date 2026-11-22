# Record209 — Incident and usage review

This support-ready record documents the bug and time evidence requested by the user. No support request has been submitted and no refund or credit has been promised.

**Confirmed application defect:** Windows file readers could block AI-BS atomic status/HLS publication. The v5.329.84 sender stopped with `STATUS_WRITE_UNAVAILABLE`; root did not send Stop. Preview had initially worked, and its off/on toggle retained the same encoder before the later failure. The HLS rename error is a separate observed output error; it alone does not establish the cause of the controller’s terminal status-write failure.

Corrective v5.329.85 requests read/write/delete sharing, adds bounded retries for classified Windows replacement failures, and uses a fixed loopback HTTP HLS route for Qt preview. Immediate replacement while a reader stays open remained unsupported in the actual fixture; bounded retry succeeded after the brief reader closed. Permanently held readers can still exhaust the bound.

| UTC, 31 October 2026 | Milestone |
|---|---|
|20:04:07.843| First retained local scope evidence; not the full session start |
|20:19:50| Prior sender terminal failure |
|20:25:40| Loopback HLS route verified |
|20:29:47.722| Corrective 85 build started |
| About 20:30; first sample 20:30:31| Native 84 GUI restore with preview off; earlier sample time parent-reported |
|20:32:17.543| Corrective 85 build finished |
|20:32:48| Corrective 85 installed; 2256 files and 4 shortcuts verified |

The corrective build took **149.821 seconds (2 minutes 29.821 seconds)**. Failure to first observed restored sample spans 10 minutes 41 seconds; failure to 85 installation spans 12 minutes 58 seconds. The first retained scope record through 85 installation spans 28 minutes 40.157 seconds. These are elapsed observation windows, not exact downtime, active model time or billable usage. Backups, offline tests, waiting, diagnosis, rebuilding and GUI verification overlap.

Computer-use calls reported `call get_window_state before using this window` and `foreground window did not report a process id`. Two state-cache precondition calls occurred around an invalidated post-input/minimized window. Activation and fresh state refresh recovered; reopening, maximizing and navigation then worked. These are recovered tool-state observations, not a confirmed platform outage or user fault. A click-argument schema mistake and local base64/tail handling mistake were separate caller-side corrections.

The first 352-case corrective test run had five fixture mkdir guard errors/denials. Its failure receipt is preserved. A narrow physical fixture whitelist correction was followed by a separate **352 tests/28 groups PASS, zero failures/errors/denials**. The final broader web bundle passed 35 checks and TypeScript also passed. These checks do not establish the final installed 85 preview outcome; that remains a separately recorded acceptance check.

**Usage attribution is unavailable:** per-task tokens, active model seconds, dollar cost, charge amount and refund amount were not measured. At 20:35:26.374 UTC, the account-limits snapshot reported 67% used across a 10,080-minute (7-day) account window. This is account-wide capacity information, not measured usage or cost for this task. The evidence does not establish an OpenAI backend outage or entitlement to a refund.


**Window closure resolved by the user:** The user explicitly confirmed intentionally closing Fortnite and all studios to prevent a failure loop. The initial 20:34–20:35 observation was unassigned pending that answer; it is now resolved as intentional closure, not a crash or platform outage. The existing sender correctly holds `NO_VERIFIED_GAME`. The user does not want a game restart or broadcast restart for acceptance. Verified v5.329.85 reopened and maximized; its checked program-preview control reports held and the canvas correctly stays blank without a verified game.


The retained read-only soak spans **20:30:59.216–20:34:11.287 UTC (192.156 seconds)** on controller 36868/encoder 31084. Frames advanced 1240→6999 and HLS sequences 15→111 with no new log errors. This precise saved interval is separate from the parent-reported earlier 20:30:31 restoration sample. At 20:36:54, the independent agent reported the same controller/encoder alive at 11906 frames/media 396.885 seconds, correctly holding `NO_VERIFIED_GAME` after game windows disappeared. That later state does not prove 85 HTTP preview activation or remote platform acceptance; no second preview soak or v85 live-game preview is claimed. The separate bounded HTTP decoder probe decoded 200 black holding frames at 1280×720 over 7.25 seconds, with advancing timestamps, no errors and no audio output. It performed no capture or broadcast control and did not test actual GUI live-game rendering.

Requested support review: “Please review this session’s recorded incidents and applicable account usage, and advise whether any adjustment is appropriate under your policies.” This is a request for review, not an automatic submission or a promise of compensation.

The JSON companion retains classifications, timing calculations and exact local evidence references. No chat secrets, stream/API keys, raw private logs or credential screenshots are included. Live trading remains disabled; audio remains generated silence with no microphone change.


The last saved runtime check at 20:43:37 UTC was before final ON confirmation: controller 36868/encoder 31084 held safely at 24003 frames/media 800.1 seconds; port 8007 had no listener, OBS process count was zero, and all four protected crypto/ledger hashes matched. The after-toggle field remains null. Earlier GUI held/blank behavior and the independent HTTP capability probe do not establish the final checkbox state or actual v85 live-game preview.


Final control boundary: preview was last observed **OFF**. Two ON attempts were blocked by `user input was detected in this window; call get_window_state before continuing`. Root stopped inputs and advised manual checkbox enabling. The user was actively editing source drafts; those drafts were not applied or assumed accepted. This is input coordination, not a confirmed outage. The installed held-GUI state and separate HTTP decoder capability passed; actual v85 live-game rendering and final ON remain unverified.


### Final user constraint and read-only state

No more screen/cursor control or GUI retries are authorized. Root stopped all computer-use input; remaining work is backend/frontend code, offline tests and read-only checks. At 20:50:17 UTC the same controller 36868/encoder 31084 remained active in NO_VERIFIED_GAME holding, advanced to 36009 frames/media 1200.3 seconds, preview last observed OFF. The later read-only sample is not a completed ON toggle. Port 8007 listeners 0, OBS processes 0, all four crypto/ledger hashes unchanged. No game, source-apply or start/stop command was sent.


### Final credential-default cleanup and verification

Two pre-existing hardcoded Twitch/Facebook stream-key defaults in the standalone broadcast component were replaced with empty strings. Exact AST reconstruction verifies only those two literal substitutions; saved settings and handlers are unchanged. The count-only RED found 2 credential-family literals; final broader JavaScript bundle passed 35 tests (contracts198 + truth204 + debranding209), TypeScript exit 0. The narrower 33-case bundle is included, not an extra run. Native 352/28 groups and the installed 85 package are unchanged. No credential rotation, historical exposure conclusion or clean-Git-history claim. Original source, private preimages and raw patches stay C-only and are never uploaded.
