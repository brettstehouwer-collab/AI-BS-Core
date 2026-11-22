# AI-BS RTX asset workflow

Authorized tooling setup, November 10, 2026 (UTC November 11). The long-term
ten-goal plan was PAUSED during setup and was explicitly resumed November11.
The asset production, import and game profiling steps below remain saved work
under the retained priority order, not completed acceptance.

## Installed and configured

- Blender 5.3.0: `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.
  Blender Foundation Authenticode signature verified. The user-supplied 5.3
  Start Menu shortcut was resolved and retained. Portable 5.2.4 LTS remains.
- Launch AI-BS with `C:\AI-BS\runtime\devtools\Blender-AI-BS-RTX.cmd`, or the
  new **AI-BS Blender RTX** Start Menu shortcut. The launcher uses a separate
  config/scripts/datafiles/extensions profile at
  `C:\AI-BS\runtime\devtools\blender-rtx\profile`, with automatic Python
  execution disabled. Existing user preferences and shortcuts are retained.
- This profile selects Cycles GPU Compute, RTX 4090 OptiX only, and OptiX
  denoising. A factory-only 128x128, eight-sample render completed, and a second
  process verified saved preferences and GPU startup defaults at 1920x1080.
  Existing .blend files retain their own render settings: select Cycles and
  GPU Compute explicitly when appropriate; the launcher does not rewrite them.
- `configure_optix.py` is a one-time, factory-startup provisioning script. It
  refuses an existing startup/preferences file; do not reset an edited profile.
- Save assets created in 5.3 as new variants. Do not assume backward
  compatibility with 5.2.4 or overwrite earlier editable masters.
- Nsight Graphics 2026.4.0.26300 installed from NVIDIA's signed MSI (exit 0).
  CLI reports 2026.4.0.0 build 39228586; version/help discovery completed.
  The `ngfx` informational commands return 1 despite valid version/help text;
  this is retained evidence, not an application capture test.
- Launch `C:\AI-BS\runtime\devtools\Nsight-AI-BS.cmd` or the new **AI-BS
  Nsight Graphics** Start Menu shortcut. No target is launched automatically.
  Local capture destination: `C:\AI-BS\runtime\devtools\nsight\captures`.
  Driver 621.14 satisfies the documented Release620 minimum. No driver,
  TDR, counter-permission, security or persistent PATH changes were made.

## First asset milestone, after explicit resume

1. Select one bounded prop. Review the current Prop01 checkpoint and approved
   native asset/cooker contracts first; reuse the working pipeline. Preserve
   existing masters, family references, provenance and original textures.
2. Work in a new named variant directory. Retain an editable .blend master,
   source/license receipt and unit/bounds metadata. Model in metres with clear
   pivots; explicitly record the engine's handedness and coordinate transform.
3. Produce game geometry, UVs and explicit collision proxies. Establish and
   record triangle/texture budgets and LOD distances appropriate to the asset;
   do not invent global budgets or substitute a texture reduction for mesh LOD.
4. Author base colour, normal, roughness and metallic maps as required by the
   existing importer. Verify sRGB base colour versus linear data textures,
   normal-map convention, texture paths and per-corner UVs. Inspect lettering
   for the retained Blender-to-DX12 mirroring caveat before approval.
5. Export through the existing supported route (the Prop01 OBJ/FBX and AIBSurf2
   cooker are precedent, not a mandate to change schemas). Reimport in a fresh
   Blender process and compare bounds, counts, UVs, orientation and references.
6. Cook a new engine asset identity, preserving old packs. In an isolated
   creator/project/save scope, verify import, selection, placement, collision,
   save and separate-process reopen. Capture real native screenshots. A Blender
   render alone does not qualify native materials, gameplay or persistence.
7. Profile a reviewed Release candidate on an isolated save. Pin executable,
   assets, target arguments, resolution, driver, build flags and hashes. Review
   actual player help and the current saved-run setup before choosing arguments;
   never point profiling at a real save or replace installed Studio launchers.
8. Use Nsight Graphics Capture to inspect resources, materials and draw calls,
   then GPU Trace for GPU passes, synchronization and memory pressure. For CLI
   trace use the installed `ngfx.exe --help-all`; explicitly set
   `--set-gpu-clocks unaltered` for the conservative baseline. Keep capture
   artifacts in the local capture directory, with a run-specific subdirectory.
9. Record trace overhead and other GPU workloads. Nsight's default GPU Trace
   disables the D3D12 debug layer and changes clock policy. Keep separate
   correctness runs with an observed debug layer and ordinary uninstrumented
   performance runs; do not reuse profiling FPS as ordinary-play qualification.
10. Preserve source, exported/cooked asset, receipts and failed evidence. Update
    the existing build monitor, checkpoint and handoff. A reviewed scoped Drive
    archive needs its own private metadata and downloaded hash verification;
    saved databases, credentials, manuscripts and original media stay excluded.

## Pending qualifications

No game capture, ordinary-play claim, new engine feature, DLSS/ray tracing
integration, engine/SDK publication or game deployment was performed during
this setup. Nsight GUI target launch and real DX12 capture are pending. Do not
request the manual gameplay tests the user already declined. Optional future
RTX Kit/Streamline work remains a separate architecture and acceptance decision.
RTX Remix's shortcut points to the installed launcher and was retained; its
classic fixed-function DX8/9 injection path is not our native DX12 pipeline.

## Official references consulted

- https://docs.blender.org/manual/en/5.0/advanced/command_line/arguments.html
- https://www.blender.org/features/rendering/
- https://developer.nvidia.com/nsight-graphics/get-started
- https://docs.nvidia.com/nsight-graphics/ReleaseNotes/index.html
- https://docs.nvidia.com/nsight-graphics/UserGuide/gpu-trace-overview.html
- https://docs.nvidia.com/nsight-graphics/UserGuide/graphics-capture-cli.html
- https://learn.microsoft.com/en-us/windows/desktop/msi/standard-installer-command-line-options

## Actual named variant checkpoint — November 11, 2026

## Blender5.3 asset pipeline checkpoint — November 11, 2026

New named Prop01 variant:13,500triangles, actual RTX4090OptiX render,
fresh exactfloat32 geometry/UV/winding reimport, new2K/1Kcookedpacks,
isolated privateSDK174 placement/collision/save/reopen and DX12 debug-layer
render/reopen passed (zero pixel differences, zero debugerrors/warnings).
37 protected files incl originals/priorfixture/preferences unchanged.
Full newvariant/evidence148member68.8MB local archive verified onD; source/
evidence cloud checkpoint separate. Original rounding-test and placement-fixture
failures retained and diagnosed, without weakening engine checks.
Art acceptance held: mirrored lettering and preview exposure; actual creator/
currentplayer, Nsight/ordinaryperformance and release gates remain open.
See docs/agent_sync/RTX_ASSET_VARIANT_2026-11-11.json. Allten+six goals active.

Tool: `engine/tools/export_blender_rtx_variant.py`; export into a NEW absolute child of an existing parent using Blender5.3 background/disable-autoexec/python-exit-code1. Fresh QA uses `--verify VARIANT --verification-report fresh_reimport_verification_v02.json`; reports are create-only. Never rerun existing output or one-time configure_optix.py. Actual namedvariant source already has physical scale; export applies only(x,z,-y), not another scaling. A new UUID identifies each cooked hero/repeated pack. Nativeproof reuses pinned existing privateSDK174 consumers and their contract, not a new player release.

## Scoped left-handed adapter and preview lighting — November 11, 2026

## Verified scoped lettering and preview fix — November 11, 2026

Explicitnew dx12-left-handed Prop01 export maps(x,z,y), reverses facewinding
with attachedUV/normals, and uses newpackUUIDs. Nativefront lettering nowreads
correctly. Actualdefaultlegacyexport/reimport staysbyteequal. Calibrated new
reviewlighting resolves topcap clipping without touching source/preferences.
FullcontrolledBlender/native81create/35reopen and zero-debug-error, pixel-exact
GPUreopen passed;44protectedfiles unchanged. This is privateSDK174 proof,
notcurrentplayer/installed/release. See RTX_LH_LIGHTING_2026-11-11.json and
RTX_COORDINATE_ADAPTER_2026-11-11.md. Next actualsourcecreator/currentplayer,
thenNsight/separate ordinaryperformance; retain declinedhuman andbrowsergates.
Allten+six goals ACTIVE/incomplete.

Reproducible controlled pipeline: recoveryPython engine/tools/qualify_blender_rtx_variant.py --output NEWchildUnderReviewedRTXdirectory --coordinate-convention dx12-left-handed. Existing outputs are refused; the driver uses fixedpinnedtools and retains failed evidence. Defaultlegacy remainsavailable andunchanged. Neverrun hardcoded oldcreatoracceptance script against existingworkspace; it has recursive-delete/old-ID assumptions.

## Current-source creator checkpoint — November11,2026

## Controlled current-source creator PASS — November 11, 2026

ActualContentView+isolatedQt6.11+pinnedSDK174 qualified innewv05scope:
selection/hiddenviewport, LHpackadopt/place, deleteUndoRedo, heroPreviewApply
UndoRedoRestore, ackSave/explicitexport, newPython/nativeepochreopen andpixel-
exactDX12reopen passed.116baseline typedrows preserved; legitimatecontentrev4→6.
Hosthandles normalexit0; noAI/networkcalls, nooriginalsave changes. Registered
OSfonts onlyin testprocess; corrected25UIlabel mojibake strings, otherASTunchanged.
Priorfailed/partialv01-v04 andread-onlydiagnostics preserved. Thisiscontrolled
sourceUI, notinstalledStudio107/currentplayer/ordinaryplay orreleasequalification.
See RTX_CREATOR_ACCEPTANCE_2026-11-11.json andCREATOR_SAVE_EXPORT_CONTRACT doc.
Next freshcurrentplayer/isolatedsave integration, thenNsight/separateordinary
performance; retainbrowser/creative/human/installed/hostedgates. Allgoalsactive.

Reproduce with recoveryPython -B engine/tools/qualify_rtx_creator.py --source-root QUALIFIED_LH_ROOT --output NEW_REVIEWED_RTX_CHILD. Seed/previousoutputs are never overwritten. AI is explicitlydisabled; actualhost/assetc/viewport andalltypedstate remainreal. Do not substituteinstalledStudio or normalhumanplay claims.
