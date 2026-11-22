# BS Game deployment — 2026-11-01

Application: **AI-BS v5.329.87**. Native engine SDK: **0.3.0**. Checkpoint format: **1**, unchanged.

## Live site

- [AI-BS site](https://ai-bs-dashboard.web.app/)
- [BS Game workspace tab](https://ai-bs-dashboard.web.app/?tab=bs_game), using the existing normal login.
- [Public playable concept](https://ai-bs-dashboard.web.app/bs-game/index.html), no login needed.

The existing Firebase project/site `ai-bs-dashboard` was grounded from the repository and verified remotely. Hosting alone was deployed; no database rules, Functions, backend services or model endpoints were deployed. Other site modules and the Unreal bridge were preserved.

The hub shows the actual native GPU frame and a dated development snapshot. It does not claim a live connection to this development PC. Browser controls: **WASD** move relative to view; **hold right mouse and drag** or **arrow keys** look; **mouse wheel** zoom; **E or left click** interact with highlighted targets. Repair the nearby core to energize traces/GPU in this concept. Catalogs pause movement. The concept resets on reload and has no native checkpoint access.

The pinned Three.js r128 renderer and MIT license are local static assets, so the loaded playground needs no external renderer CDN. The native package includes the same assets. The original supplied sketch and new reference fragment remain local provenance records; the improved public copy is the evolving concept.

Production build/typecheck and three focused frontend tests passed. Eight declared hosted files matched the current production outputs. A fresh Chromium profile passed ten WebGL/render/input/interaction checks, including actual right-drag and visible-target clicking. The main site loaded with its ordinary authentication gate; no login or protected-workspace bypass was performed. Browser WebGL may use software rendering and is separate from the RTX DX12 proof.

Actual publish commands (from the repository root, with the frontend build run in its directory):

```powershell
npm.cmd --prefix frontend run build
npx.cmd -y firebase-tools@latest deploy --only hosting --project ai-bs-dashboard --config frontend/firebase.json --non-interactive
python frontend/tests/playground_smoke.py --url https://ai-bs-dashboard.web.app/bs-game/index.html
```

## Deployed native program

Verified executable: `C:/AI-BS/native_studio/releases/v5.329.87/AI_BS_Studio/AI_BS_Studio.exe`.

Five existing Desktop/OneDrive Desktop/Start Menu links were updated to that version after verification. Original shortcut bytes and all older release directories were retained. Open **Engineering & Specialized Labs → AI-BS Game Engine Build** for the monitor, browser concept launcher and **Launch native motherboard world (PC / DX12)**.

The fresh frozen build contains 74 native modules and declared assets. It bundles the concept, local renderer/license, headless player, native DX12 preview and compiled shaders. The original package build completed in about 109 seconds. Later renderer and playground-control additions have separate copy/readback and runtime evidence. Existing host services remain external; the package does not bundle backend code, databases, memoir, ledger, saves, private keys, model weights or developer logs. No signing action was performed.

The frozen game workspace was executed with `--game-build-smoke REPORT_PATH`: real Qt widgets and worker refresh, bundled-resource resolution and screenshot passed without starting application services. The copied DX12 executable then ran directly from the package on RTX 4090, with resize/minimize/readback and debug-layer checks. The packaged HTML passed the same ten browser interaction checks through a local file URL.

The current native renderer is a free-flight geometry preview, separate from persistent scene editing. Controls: WASD/arrows move, right-drag look, Space/Ctrl elevation, Shift speed, Esc close. Next work connects saved entities and edits to the visible scene.

## Reproducible future packaging

`scripts/build_native_game_release.py` freezes the current native graph and explicit assets into a fresh staging tree. `--include-player` includes the headless player and native preview when available, requiring both shaders for the latter. Existing release/stage directories are never overwritten. Use a fresh authoritative application version and work path for a new full frozen build; the current release is already deployed.

The historical `build_native_web_parity.py` baseline guard remains intact. This scoped game release makes no full web/native parity claim. The exact original builder used for v5.329.87 is preserved as `backups/native_game87_20261101_gamehub/builder_used.py`; the current helper adds future renderer staging and has eleven passing focused tests.

## Local evidence and storage

- `engine/out/renderer_verification.json`, `motherboard-render.bmp/png`
- `engine/out/site-verification/hosting_verification.json`, `playground-live.json/png`, `site-cold-entry.json`
- `engine/out/native-release-final.json/png`, `packaged-native-renderer.json/bmp`
- `engine/out/native-playground-verification/playground-live.json/png`
- `backups/native_game87_20261101_gamehub/`: frozen plan/build logs, static package verification, shortcut backup/readback, renderer addon and controls update receipts.

The source monitor reads local evidence and bounded output sizes without network polling. It also tracks C:/D:/E: free space. Graphics Tools installation temporarily used Windows servicing space and finished without reboot; no user files or old releases were deleted. Public output still duplicates existing large media/update assets; private/binary hosting exclusions remain in Firebase configuration. Source/evidence Drive backups exclude large build/package output. Google Drive account quota is not exposed by the available connector.


## Retained M3 deployment — Studio5.329.94 / SDK0.8

Current existing desktop/StartMenu shortcuts target94. The game workspace has a capability-checked Play First Boot chapter button, using a dedicated default save and offline native player. Actual frozen smoke,14asset/4criticalmodule readback, packaged36chapter+23M2process tests and five backed-up shortcut readbacks pass. Receipts are under backups/native_game94_20261101_m3. Studio93 was never activated; it predates corrected hints and is retained as development. Prior marked milestones and user saves remain intact. Public website remains5.329.87; no web/native parity, full20–30minutealpha, clean-machine or universal power-loss certification is claimed.
