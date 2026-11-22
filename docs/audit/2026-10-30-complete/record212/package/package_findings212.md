# October7 package audit — Record212

Read-only static review; no program, audio device or installer was launched.

Installed folder: 10,591 files / 7,146,613,269 bytes.

Recovered app_native.py is compiled-source-equivalent to installed Native.exe. It differs from the older DAW.exe.

- **HIGH O7-PKG-001 — Build and launch recipes select a different application than the current native release** A routine documented build/launch can yield an older or different UI/workflow, making fixes appear missing and release reproduction ambiguous. Remedy: One canonical native build/launch command targeting app_native.py; explicitly named separate legacy target; pin entrypoint and source manifest in every release.
- **HIGH O7-PKG-002 — Native release includes an unnecessarily broad environment and unrelated AI-BS backend code** The installed folder is7146613269bytes/10591files; extra libraries enlarge maintenance, distribution and audit surface. Presence does not establish that trading, network or backend modules run at startup. Remedy: Build in a clean, pinned minimal audio/Qt environment; explicit module/resource allowlist; fail package audit if AI-BS backend or unrelated finance/web libraries appear. Separate optional AI workers from realtime DAW.
- **MEDIUM O7-PKG-003 — Native build omits default song/stem assets and depends on the existing overlay install** A clean native distribution does not reproduce the installed default session. Missing assets are silently skipped, leaving empty tracks or unexpected initial state. Remedy: Bundle declared demo resources or provide a verified first-run demo project; keep user sessions/takes separate from installed immutable resources; smoke-test from an empty install directory.
- **MEDIUM O7-PKG-004 — Deployment overlays a mixed release and reports signature results without enforcing them** Old entrypoints/resources remain side by side and partial copy/signing failure can be reported as successful deployment. Current installed signatures were independently Valid on this machine; no current tampering claim. Remedy: Stage a new version directory, verify all bytes/assets/entrypoint/signature first, switch launchers after validation, retain prior version for rollback; treat signing failure as build failure.
- **LOW O7-PKG-005 — Both installed executables lack file/product version metadata** Users cannot distinguish the two builds reliably from Windows file properties; filenames and dates are inadequate release identity. Remedy: Embed FileVersion/ProductVersion/product description and publish release manifest containing source hash, entrypoint, dependency lock and artifact hash.
- **MEDIUM O7-PKG-006 — Architecture verification prints an unconditional conclusion that exceeds its checks** DLL presence cannot prove hardware latency, selected runtime mode, no server, or workflow correctness. The installed application is a Python312-hosted native Qt GUI, not an all-C++ implementation. Remedy: Report measured checks individually with PASS/FAIL/UNVERIFIED and nonzero exit on required failures; test runtime/service claims separately from package presence; distinguish native widgets from Python DSP/runtime implementation.

Positive: both signatures validate on this machine; Qt/PortAudio/libsndfile/pedalboard files exist. No Chromium/WebEngine/WebView/Node engine binary found.

See package_findings212.json for exact source-line and frozen-artifact evidence. Runtime audio/latency/plugin behavior remains unverified.
