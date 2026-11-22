# AI-BS Full-Stack Connection & Consolidation Audit — 2026-11-22

Prepared by: **Claude Code (Claude Opus 5.5, Anthropic)**, branch `codex/audit-v532976-20261031`.

Scope: backend (FastAPI `AI_BS_Backend.py` on :8080, Go gateway :8000), web frontend
(Vite, entry `frontend/main.jsx` → `frontend/App.jsx`), native PyQt6 studio
(`native_studio/app.py`), creative tools. Read-only audit; nothing was changed.

Method (all reproducible):
- Static: every backend route decorator (1,452) vs every `/api/...` string in the
  frontend (707 distinct) and native app (57).
- Reachability: import graph walked from the real entry points (`main.jsx`,
  `src/writer_main.jsx`) to split **live** from **dead** files.
- Live probes against the running backend (404 = route absent; 403 on some
  prefixes is an auth wall that hides whether a route exists, so those were
  settled by source search instead).
- `tsc --checkJs` on the creative files for undefined names and type misuse.

Classification follows AGENTS.md: VERIFIED (proven by probe/source), PROPOSED (fix).

---

## P0 — Broken behaviour a user can hit today (VERIFIED)

| # | Where (live file) | Problem | Evidence |
|---|---|---|---|
| 1 | `components/ProductionBreakdownModal.jsx:83,127`, `components/StagePlayBreakdownModal.jsx:40` (Writing Studio) | Use `window.env?.BACKEND_URL`, which is never set, so they always call `http://127.0.0.1:8000`. They work only on this PC and fail from the phone or hosted site, and they skip the app's backend/auth selection. | `window.env =` assigned nowhere; tsc TS2339 |
| 2 | `components/BsMediaCreatorTab.jsx` (BV-Media Studio) | Calls `/api/v1/media/wan/synthesize`; no such route exists. | no backend source match |
| 3 | `components/MediaStudioTab.jsx` | Calls `/api/v1/media/ipc/buffer/allocate`; no such route. | no backend source match |
| 4 | `components/ComfyUIWorkflowTrigger.jsx` | Proxies to port **8002**, which is ChromaDB, not ComfyUI (8189). | live probe **410** |
| 5 | `components/CryptoSwarmMobileController.jsx` | Calls engine `/api/v1/telemetry`, `/api/crypto/set-parameters`, `/api/crypto/force-swap`; the engine on :8007 serves only `/health`, `/api/live-telemetry`, `/api/scenario-mode`. Buttons look functional but can't act. | probe **404** |
| 6 | `src/clients/DennisBellMobileRemote.jsx` (client-facing RecDebut remote) | `broadcast/start`, `/pause`, `/stop`, `/single_test`, `replies/sync` under `/api/v1/recdebut` don't exist in the backend. | no backend source match |
| 7 | `components/RapidApiReconTab.jsx` | `/api/googletrends/interest`, `/api/thumbtack/...`, `/api/yellowbot/...` | probe **404** |
| 8 | `components/BrettDataTab.jsx`, `VectorVaultManager.jsx`, `TheatricalMicClient.jsx`, `TheatricalStageSwitch.jsx` | Proxy to :8001 (vault/theatrical); nothing listens on 8001. BrettDataTab also uses :3001 (down/held). | probe **500**, port down |
| 9 | Top navbar: 70 industry sub-tabs (`navigationConfig.js` hubs such as *Deep Tech & Science*) | Keys like `medicalbioinformatics` have no tab, so `App.jsx:743` (`?? tabs[0]`) silently opens **64-Specialist Swarm Explorer**. | key cross-check |
| 10 | Buttons jumping to tabs that don't exist (same silent fallback) | `TopNavbar.jsx:803` and `AdminSharedDriveTab.jsx:696` → `video_agent`; `GlobalCommandPalette.jsx:36` → `documents`; `SimpleDashboardPortal.jsx:167` → `media_vault`, `:178` → `definitions_module` | key cross-check |
| 11 | `App.jsx:777` overlay route | `lazy()` is created inside render, so React gets a new component type every render (remount and state loss). | source |
| 12 | Creation Suite (`UniversalCreationSuite.jsx:36`) | The entire suite, local-only tools included, refuses to open without a Firebase sign-in. That blocks offline writing. | source |

## P1 — Edits that silently don't take effect (likely the "tweaks don't stick" cause)

1. **Shadowed backend handlers (VERIFIED).** Routers are included around lines
   2067–2191, before the same paths are re-declared on `app`, so the first
   registration wins and the later handlers are dead code:
   - `POST /api/chat`: the live one is `routers/chat_router.py:171`; `AI_BS_Backend.py:9001` never runs.
   - `GET /api/comfyui/view`: the live one is `routers/comfyui_router.py`; `AI_BS_Backend.py:10833` is dead.
   - `POST /api/v1/emails/send`: the live one is `routers/email_client_router.py`; `AI_BS_Backend.py:8018` is dead.
2. **Four mirrored frontend trees.** `frontend/components`, `frontend/src/components`,
   `frontend/src/components/components` and `frontend/components/components` are kept
   byte-identical by `verify-mirror-parity.ps1` (canonical source `src/components`).
   - The live app imports from **both** `components/` (233 live files) and `src/components/` (63 live files).
   - An edit in one tree is live or dead depending on which importer is used. It is
     overwritten or flagged unless all mirrors are synced.
   - 532 redundant copies in total.
3. **Dead creative code that looks real.** `BullshitCreationSuite.jsx`, `FireWritingTab.jsx`,
   `UnifiedCreationHub.jsx`, `UniversalCommandPalette.jsx`, `BullshitKnowledgeSuite.jsx`,
   `src/main.jsx`, `FEExpressDriverReports.jsx`, `CryptoTraderTab.jsx` and
   `useUnifiedTelemetry.js` are not reachable from the app. Fixes made in them change nothing.
4. **Leftover backend copies**: `AI_BS_Backend_shadow.py`, `routers/rec_debut_router (2).py`,
   and ~20 `*.pre_security_audit_20261022.bak` files beside live code.

## P2 — Consolidation candidates (PROPOSED)

| Area | Live overlapping components | Proposal |
|---|---|---|
| Writing | `PlaywrightTab` (thin wrapper) → `ScreenwritingTab` (**226 KB monolith**), `industry_suites/WritingSuiteTab`, modals (Novelizer, TableRead, Production/StagePlay breakdown) | Keep the Screenwriting core and split it into editor, export, AI tools and breakdowns modules. Drop the industry copy and the dead writing tabs. |
| Media/video/ComfyUI | 15 live: `VideoStudioTab`, `VideoSuiteTab`, `VideoStreamingTab`, `MediaStudioTab`, `BsMediaCreatorTab`, `ComfyUIStudio`, `ComfyWorkspaceTab`/`ComfyStation`, `ComfyUIWorkflowTrigger`, `ComfyUIRenderWidget`, `UnifiedMediaVaultTab` | One Media Studio with three panes (Generate via ComfyUI/WAN, Edit/Preview, Vault). Fix #2–#4 while merging. |
| Chat | `ChatTab` (437 KB), `MobileStehouwerChat`, `UnifiedChat`, team chat drawer/modal | Choose one chat core; make mobile a layout of it, not a fork. |
| API base URL | 90 live files hard-code `127.0.0.1:8000/8080/...` despite `config/api.js#getEffectiveApiBase()` | One `apiFetch()` helper (base URL, auth, timeout). This removes the whole P0-#1 class. |
| Navigation | `navigationConfig.js`, `MobileNavDrawer`, `Sidebar`, `TopNavbar`, two command palettes, native `navigation_registry.py` | One shared key registry; make unknown keys show a "not available" card instead of `tabs[0]`. |
| Styling | 195 components use inline `style={{…}}`; 38 CSS files | Move to theme tokens and shared layout primitives, which fixes inconsistent spacing and heights. |

## Native PyQt6 studio — healthy (VERIFIED)

- All 57 native `/api` calls match backend routes, and no referenced icon/image files are missing.
- All 59 registry tabs map to a dedicated view; none hit the Executive Cockpit fallback.
  Views are created lazily.
- **One cost (P3):** `app.py` imports about 40 view modules at startup even though views are
  built lazily. Moving those imports inside `_get_or_create_subview` would cut cold-start time.
- **One parity gap (P3):** the native app has no equivalent of the web's broken features above,
  but the web Writing Studio's breakdown modals (P0-#1) have no native counterpart either.

## Recommended fix order

1. P0-#9/#10/#11 (navigation fallback, missing tab keys, lazy in render): small, safe, visible everywhere.
2. P0-#1 plus the `apiFetch` helper, applied first to the creative tools.
3. P1-#1: delete or mark the three shadowed `AI_BS_Backend.py` handlers so nobody edits dead copies.
4. P0-#2–#8: wire or remove each dead endpoint (decide per feature whether it is still wanted).
5. P1-#2: collapse the mirrored trees to one source of truth, with a guarded migration
   (the parity script and the Android/iOS bundles depend on the layout).
6. P2 consolidations, starting with Media Studio.

Not covered: runtime behaviour behind sign-in (403-walled routes were source-checked only);
Android/iOS bundle copies; game engine; business daemons.

---

## Addendum — formerly password-protected sub-tabs (re-audit, 2026-11-22)

**Change under review (VERIFIED):** `getUserTier()` in all four mirrored
`accessControl.js` copies (identical hash, modified 08:28) now returns `ADMIN`
for `localhost`/`127.0.0.1` *before* checking for a signed-in user. Every key in
`TAB_PERMISSIONS` (terminal, vms, security_monitor, unified_crypto,
deep_learning_studio, system_health, system_economics, brett_data_hub,
agent_memory, creation_suite, executive_cockpit, …) now opens locally with no
sign-in. Hosted sites are unaffected.

### Findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| A1 | P0 | **Tabs open, but their data calls fail when not signed in.** The global fetch interceptor (`main.jsx:38`) only attaches an ID token for a signed-in, email-verified admin. The backend still enforces auth, so an unsigned local session sees empty or erroring admin tabs. Of 532 distinct `/api` paths in live files, **314 return 403** unauthenticated. | re-probe of :8080 |
| A2 | FIXED 2026-11-22 | **Two in-tab password prompts (now removed from all 4 mirrors; rebuild needed to purge dist)** and use a hard-coded password in client code.** `BetaAnalyticsTab.jsx:75` (Telemetry Suite) and `UnifiedMediaVaultTab.jsx` compare input to a literal string. That string ships in `dist/js/BetaAnalyticsTab.*.js` and `UnifiedMediaVaultTab.*.js`, so anyone can read it. It protects nothing; real protection is the backend 403. Recommend removing these prompts (they still block you locally) and rotating that password if it is reused anywhere. | source + built bundle |
| A3 | P1 (security) | Both gates treat any email containing `julie` as always unlocked (`userEmail.includes('julie')`). | source |
| A4 | P1 | `getUserTier` now has dead logic: `isLocalDesktopAdmin` can never be true after the early return. | source |
| A5 | P1 | `UnifiedMediaVaultTab` falls back to `http://localhost:8000` and Beta Analytics' `/api/audit-ledger/*` and `/api/network-telemetry/*` routes all exist but are 403 unauthenticated (same as A1). | probe 403 on :8080 and :8000 |
| A6 | P2 | `DigitalStorefrontTab`'s "unlock" is a PayPal PDF purchase flag, not a password gate. No change needed. | source |

### Other failing endpoints found by the re-probe (live files)

GET probe only, so some 404s are POST-only routes or endpoints served by
other daemons (VST :`aibs_vst_daemon.py`, broadcast `/api/windows`,
Ollama `/api/tags`, crypto engine `/api/live-telemetry`). The items below
are confirmed missing from the main backend or point at a down service:

- Creative: `ScriptToBookNovelizerModal` → `/api/novelizer/get_drafts` (404).
- `VideoStudioTab` → `/api/video/batch_status` (404).
- `FEExpressPinPortal` → `/api/v1/fe-express` (404).
- `ThoughtfulFrictionModal` → `/api/ws` (404).
- `LearningMaterialHub` → `/api/proxy/3000` (404).
- Unreachable (connection error): `/api/spaces/overview`,
  `/api/system/matrix/doctor`, `/api/v1/diagnostics/tshark/mining-audit`,
  `/api/advertising/aeo`, `/api/clients/joey_hamilton/secure-memory`.
- Previously reported :8001/:3001/:8002 proxy failures are unchanged (500/410).

### Recommendation

To make the unlocked tabs actually work locally, pick one:
1. Sign in once locally (fastest; the interceptor then supplies the token), or
2. Add a backend loopback-only admin bypass guarded by the client IP
   (`127.0.0.1`) **and** the absence of proxy headers, so tunnelled traffic
   through Cloudflare/Nginx can never use it.
Then delete the two client-side password prompts (A2/A3).

---

## Addendum 2 — Fix-list pass and audit of `AI_BS_COMPLETE_ARCHITECTURAL_MANUAL.md` (2026-11-22)

### Fixed (commit `c23fe187` plus follow-up)

| Manual item | Fix |
|---|---|
| 3 shadowed handlers | Removed the `/api/v1/emails/send` and `/api/comfyui/view` duplicates and the `/api/chat` decorator from `AI_BS_Backend.py`; `/v1/chat/completions` is kept. This takes effect on the next backend restart, with no behaviour change because those handlers never ran. |
| BsMediaCreator WAN, MediaStudio IPC buffer | No real backend route exists, so the buttons now report "not connected" instead of calling a 404. |
| ComfyUIWorkflowTrigger → :8002 | Now calls `/api/comfyui/generate` with real workflow files (`flux_image_generation.json`, `wan2.1_i2v_lightx2v_fixed_workflow.json`) and shows HTTP errors. ComfyUI (8188/8189) was not running at test time. |
| CryptoSwarmMobileController | Status now reads the engine's real `/api/live-telemetry` (read-only). Set-parameters and force-swap report "not available"; no trading endpoints were added. |
| Mobile broadcast remote | Stop/Pause now call `/broadcast/cancel`, and reply sync calls `/sms/sync-replies`. Start broadcast and single test are deliberately **not** wired: they would send real outbound messages, and campaign sends are on hold. |
| Blocking sleeps | 144 `time.sleep()` calls inside `async` handlers (`industry_tools_router.py` 132, `functional_utilities.py` 12) froze the entire backend for 0.5–1.5 s per call. They are now `await asyncio.sleep()`. |

### Manual accuracy check

| Manual claim | Measured | Verdict |
|---|---|---|
| 73 registered tabs | 74 entries in the `App.jsx` `tabs` list | Close (off by 1) |
| 282 live components | 358 files reachable from the entry points (this count includes non-component modules) | Different counting method, not an error |
| 118 routers/modules | 87 router files (excluding `.bak` files and copies) plus modules | Plausible as a combined count |
| 1,168+ routes | 1,452 route decorators in source (this includes duplicates and shadowed handlers) | Consistent with the manual's "1,168+" |
| 28-model Ollama fleet | 30 models installed now | Minor drift |
| 167 native modules | 167 | **Exact** |

### Overstated features (the manual lists these as working tools, but they return fixed or random data)

- **`industry_tools_router.py` (141 routes, behind the 70 industry verticals):** 198 `random.*` calls. Most `telemetry_scan` and `autonomous_override` endpoints return fixed or random results. For example, `financialhedgefund/autonomous_override` returns "Algorithmic Trading Swarm Engaged" without doing anything. A few scans make real public API reads (e.g. CoinGecko prices).
- **`functional_utilities.py` (12 routes):** every handler carries the comment "Mock intense logic delay" and returns `SUCCESS` with a random number (PLC override, vulnerability scanner, hospital beds, grid shedding, and others).
- **`wan_media_router.py` `/t2v/generate`:** waits about 2 s and marks the job `RENDERED_ONLINE` with a filename, but renders nothing and never calls ComfyUI. Real renders go through `/api/chat/films`.
- **`/api/phase4/vm/list`:** returns two hard-coded VMs, always "running".
- The manual sections that describe these as working should be relabelled **SIMULATED / DEMO** until they are wired to real logic.

### Still open

- `rec_debut_router.py` has 2 blocking `time.sleep` calls in async handlers. They are unchanged because they sit on the sending code path.
- The 70 industry sub-tab keys still have no tab; they now show the "isn't available yet" card.
- Mirror-tree collapse, Media Studio consolidation and the `apiFetch` helper (P1/P2 above).
