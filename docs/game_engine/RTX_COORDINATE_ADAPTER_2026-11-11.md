# RTX-COORD-20261111 — Explicit Prop01 left-handed adapter

Status: VERIFIED for the new isolated Prop01 variant; no global engine/world migration.

Requirement: RTX_ASSET_WORKFLOW steps2,4,5,6; preserve original masters/oldpacks,
verify coordinate/texture/winding fidelity and real native readback.

Original design: `(x,z,-y)` proper rotation plus source triangle order. Retained
native camera uses DirectXMath LookToLH. Actual cooked texture pixels match the
original top-down PNG and every cookedUV matches declared bottom-left conversion.
Composing the old adapter with actual camera flips the topchart's signed screen
area to -0.7597455666. The rotation itself is not a reflection.

Decision: add explicit `--coordinate-convention dx12-left-handed`, mapping
positions AND normals `(x,z,y)`, determinant-1, and reversing face corners to
`i0,i2,i1` with each corner's UV/normal index. NewUUIDpacks only. The original
RHeditable master remains unchanged. Default `legacy-rotation` remains compatible.

Affected components: exporter, independent review-lighting tool and bounded
qualification driver under engine/tools. No renderer, camera, shader, save schema,
SDK binary, existing source asset, six-shared-placement binding or old pack changes.

Compatibility: actual default-option Blender export/reimport retained every OBJ
v/vt/vn/f row byte-for-byte. NewLHpack uses the existing AIBSurf2 contract. Existing
worlds continue referencing their prior immutable identities. No mass replacement.

Acceptance observed: actualBlender5.3RTX4090OptiX export; fresh exactfloat32
triangle-corner position/UV/winding reimport; local textures and measured sRGB/
Non-Color assignments; new2K/1Kcooks;81nativecreation/35freshreopen assertions;
offscreenDX12debuglayerzeroerrors/warnings and0pixel-difference fresh GPUreopen.
New nativefront lettering is readable/unmirrored.44protectedfiles unchanged.

Preview lighting: inherited source lights are hidden only in new review scenes;
a neutralworld and three calibrated area lights replace additive illumination.
512quarter/top review displays cap markings without clipped highlights. This is
technical visibility review, not final artistic/user acceptance.

Evidence: docs/agent_sync/RTX_LH_LIGHTING_2026-11-11.json; new isolated run
D:/AI-BS-Game-Resources/RTX_Variants_20261111/Prop01_LH_20261111_v01.
Prior diagnostic and failed evidence remain in their original run. Remaining:
actual creator/currentplayer, Nsight/performance, installed/hostedrelease and
human likeness/caption/pacing gates. No public deployment or business activation.
