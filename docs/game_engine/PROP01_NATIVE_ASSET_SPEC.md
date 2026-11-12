# Prop01: source scale, export and placement specification

Status: PLANNING / SOURCE INSPECTION ONLY. Local date 2026-11-04; evidence observation 2026-11-05T03:26:18Z. The creator explicitly chose Continue planning again in this chat. No modeling, texture conversion, import/cook, build, editor change or runtime test was performed. This supplements PROP01_NATIVE_OPENING_PLAN.md and retains original checkpoints3-8.

## Source now located

Root: C:/Users/footb/Documents/antigravity/lucid-bardeen/photogrammetry_props/Prop01_TUF_Solid_Capacitor/.

- scripts/generate_prop01_photoset.py: source construction, procedural materials and synthetic capture generation. Inspected selected geometry/material/camera/save sections; it was not executed.
- metadata/Prop01_TUF_Solid_Capacitor_Source.blend: existing editable source, 8,466,107 bytes. Existence/length verified, but this planning review did not open it or establish that its object graph exactly matches the generator.
- metadata/capture_manifest.json: found in metadata, not the prop root. It describes60 rendered views at2100x1400 with elevations16-71degrees. EXIF and camera/lighting descriptions remain synthetic authoring metadata, not measured physical calibration.
- Raw reconstructed delivery: C:/Users/footb/Documents/AI-BS_Unreal_Demonstration/Photogrammetry/Prop01_TUF_Solid_Capacitor/20261105T024638Z/. FBX/OBJ/PNG/MTL/.rcInfo and reconstruction receipt remain the retained comparison.

The earlier root-directory manifest lookup did not find this metadata file; the correct path is now resolved. Do not regenerate the60inputs simply because a root-level manifest was absent.

## Source-unit interpretation

Generator lines536-539 explicitly set MM=0.01: one nominal millimetre is represented by0.01Blender units. Under a metre interpretation this is ten times its nominal physical length.

| Feature | Source numeric length | Nominal authored physical length | Basis |
| --- | --- | --- | --- |
| PCB coupon edge | 0.136 | 0.0136m /13.6mm | hs=6.80*MM; cube span2*hs, lines808-814 |
| PCB thickness before bevel | 0.0085 | 0.00085m /0.85mm | thick=0.85*MM, line809 |
| Maximum can diameter | 0.063 | 0.0063m /6.3mm | profile radius3.15*MM, lines552-563 |
| Can top above coupon top | 0.0825 | 0.00825m /8.25mm | profile maximum z8.25*MM, lines566-567 |

These are generator design dimensions. They do not identify or measure the exact capacitor installed on Brett's motherboard. The top-above-board dimension is not the can's own height: the profile begins above zero. Inspect the complete source when authoring the cleaned master.

For a direct source-model derivative, a0.1normalization factor follows from this declared numeric convention, subject to verifying saved object transforms and scene units. For the reconstructed model, scale is independent: identify the actual PCB corners/plane, measure its edge L, then use s=0.0136/L for the nominal physical variant. Do not use the artifact skirt or arbitrary reconstruction bounds as that measurement. Check the can diameter as a second reference and record any nonuniform reconstruction error.

Keep three transforms explicit: source normalization; coordinate conversion; gameplay instance enlargement. Do not bake an arbitrary giant-world scale into the source dimensions.

## Native limits discovered before attempting import

| Data | Raw Prop01 | Existing native hard limit | Planned preparation |
| --- | --- | --- | --- |
| OBJ source bytes | 50,114,386 | 33,554,432bytes /32MiB | Simplify and export a new triangulated OBJ; preserve raw export. |
| Vertices | 237,451 recorded | 100,000 | Reduce to an economical game mesh and count exported records. |
| Triangles | 474,898 recorded | 100,000 | Start a hero study around10-15ktriangles and compare a lighter repeated variant; these are proposed art targets, not tested performance promises. |
| UV records | 253,322 recorded | 100,000 | Preserve seams while bounding exported vt records. Final post-export admission, not Blender's displayed face count, decides compatibility. |
| Full4096RGBA mip chain | 89,478,484bytes /85.33MiB | 32MiB per image and32MiB complete surface payload | Keep4Kmaster; prepare a smaller native derivative. |
| Full2048RGBA mip chain | 22,369,620bytes /21.33MiB | Same shared surface budget | Candidate hero texture; geometry/corner/material overhead must also fit. |
| Full1024RGBA mip chain | 5,592,404bytes /5.33MiB | Same shared surface budget | Candidate repeated/small-prop texture, compared at actual gameplay distance. |

The12.3MBcompressed PNG file size does not establish decoded fit. The4096base level alone is64MiB. Calculations above sum complete square RGBA8 levels down to1x1; they are arithmetic estimates, not a cook, GPU memory measurement or runtime test.

Native source inspected: engine/include/aibs/assets.hpp (input/vertex/triangle/material limits), image_assets.hpp (32MiBper-image limit), surface_codec.hpp (32MiBsurface limit), src/surface_assets.cpp (bounded UV records), src/image_assets.cpp and apps/asset_cooker.cpp (decode/admission accounting). Retain these limits; no engine-limit expansion is proposed to admit this raw prop.

## Actual existing asset route

Triangulated OBJ + explicit AIBMAT2 + bounded PNG -> aibs_assetc --cook-surface -> AIBSurf2/AIBCAT2 four-file pack -> inspect/adopt into immutable project store -> FirstBootAssetPlacement -> Creator Preview/Apply/Undo/Redo/Save -> new-process restart and isolated Play.

Use the current compatible SDK tools when implementation resumes; do not copy the historical SDK0.10path from older examples. GLB support already serves a bounded character path; a new staticGLBimporter is not required for this prop.

Export positions in metres with+Yup and declare UV origin explicitly. Native import does no hidden unit/axis conversion. For a Blender+Zup source, a proposed proper rotation maps(x,y,z)to(x,z,-y); verify with an asymmetric marker, normals, winding and a numbered corner before publishing. Unreal's native-world adapter is UE(X,Y,Z)=100*(nativeX,nativeZ,nativeY). Do not apply both the exporter axis conversion and a second duplicate conversion.

OBJmtllib is inert. Supply every usemtl name in AIBMAT2 and each PNG as a bounded basename relative to that declaration. Keep the complete source/export materials for Unreal; native static shading currently supports albedo/emission with authored lights. It does not sample roughness/metallic/AO maps or use stored tangents for active normal mapping. Better Unreal shading does not establish feature parity in nativeDX12.

Use the warm_beginning content profile and existing AIBD3 placement binding; retain legacy packs/readers and monotonic document versions. The128MiBencoded/decoded dependency budgets are additional closure limits, not an exemption from individual32MiBimage/surface limits. Include license/provenance and a new asset/content revision in every fresh immutable pack.

## Placement and collision decision

The existing warm-opening capacitor reference is reused six times by engine/games/warm_opening.cpp:101-107. Swapping that shared reference would replace all six visuals. The current contract expects a .30m-radius shell atY=.275..1.125m, board-mount pivot, pins no lower than-.04m and an explicit .205/.42/.205m collision core centered atY=.7m above each placement (warm_opening.hpp:5-11).

The reconstructed coupon/can proportions do not automatically meet that shell contract. Merely matching diameter cannot guarantee matching height, base or collision. Plan the first native test as an independent visual placement and deliberately authored matching proxy in a disposable chapter branch. Compare existing walking space and interaction reach before deciding whether a fitted shell-only variant or new proxy is appropriate. Do not redirect all six bindings or alter normal saved chapters as the first test.

Keep optional decorative rows outside doors, fault-selection rays and Adam's authored routes. Visual importing creates no physics. Source boards/contacts/pins need no individually collidable triangles. A proposed simple proxy must visibly fit its intended obstruction and preserve safe approach, jump/pass-by, door occupancy and fall recovery.

The capacitor's visible state can support existing diagnosis/isolation/repair/bypass actions. Detailed geometry does not create a new mandatory quest or silently change the electrical simulation. Adam's authored cues continue to reflect actual game conditions and saved choices.

## Exact future acceptance sequence

1. Compare the existing procedural source and raw reconstruction; retain all originals and choose/record the base for the game derivative. Capture all-side cleanup previews and measured authored bounds.
2. Export the triangulated native variant plus proposed2K/1KPNG, explicit materials, license and source provenance. Count bytes/vertices/UVs/triangles before cooking; keep headroom for the complete payload.
3. Cook/inspect a fresh surface pack and verify malformed/oversized/dependency-corrupt rejection and failed replacement rollback using the existing tools.
4. In the separate Unreal copy, import the accepted game variant with authored surfaces and simple collision; inspect close-up and a repeated row. Save/reopen placement and separately test session-only repair/bypass.
5. In the native disposable chapter, adopt/place with explicit proxy and verify visual/movement/selection/light behavior, then Preview/Apply/Undo/Redo/Save and source-independent fresh-owner restart. Retain companion, light, media and save identities.
6. Walk both current native routes/camera modes, then measure the intended instance count. No claim of hardware instancing or constant frame cost follows from reusing a pack reference.
7. Record screenshots and slow walkthrough of the actual tested packages, resource measurements and limits. Complete the retained native qualification/pacing/likeness/caption/package/backup gates from the parent plan before whole-goal closure.

No asset has yet been exported to these proposed targets or qualified by this planning checkpoint. Installed107, held108/109, unpublishedSDK174 and all original family references/saves remain as previously recorded. C:258.01GiB/D:86.76GiB free observed; E unused. A read-only PowerShell estimate first hit a syntax error, was corrected once, and returned the mip arithmetic above. No input asset was modified.
