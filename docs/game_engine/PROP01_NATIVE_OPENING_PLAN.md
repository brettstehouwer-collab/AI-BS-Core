# Prop 01 and the native Warm Beginning: integration plan

Planning checkpoint PLAN-PROP01-20261104. Local date: 2026-11-04 (America/New_York). Recorded: 2026-11-05T03:14:33Z.

Status: PLANNING ONLY. No modeling, Unreal import, engine build, runtime qualification, launcher change or release is performed by this document. The complete original checkpoints 3-8 remain the goal; the existing opening-first priority plan governs native work. The recent Unreal request permits a bounded visual demonstration, without replacing native acceptance.

## Evidence and current limits

- Authoritative continuity: PROJECT_INDEX.md, the latest relevant docs/CODEX_HANDOFF.md entries, engine/BUILD_STATUS.md and engine/out/warm_beginning/monitor_summary.json. The current checkpoint pointers take precedence over introductory historical version paragraphs.
- Current recorded native state: installed Studio107; held108/109; SDK0.17.4 R2 Release build and 129 registered Release tests passed, Debug build passed, Debug suite stopped after 39 passes. Remaining camera/route cases, installed/relocated consumers and Studio110 delivery are unfinished. The earlier third-person return failure was not reproduced; its cause remains unproven. No live process is inferred from these older records.
- Prop reconstruction: C:/Users/footb/Documents/AI-BS_Unreal_Demonstration/Photogrammetry/Prop01_TUF_Solid_Capacitor/20261105T024638Z/RECONSTRUCTION_README.md and reconstruction_receipt.json. Sixty synthetic Blender views aligned; raw mesh has 237,451 vertices / 474,898 triangles and a 4096 x 4096 diffuse texture. The receipt reports independent structure/UV checks and a real disposable Blender import. This review did not rerun those checks.
- Synthetic camera EXIF is not real camera calibration. Board-edge skirt, uneven casing and unseen underside need review. Physical scale remains unconstrained. The existing diffuse image does not establish measured normal, roughness, AO or metallic maps.
- Separate Unreal scope: C:/Users/footb/Documents/AI-BS_Unreal_Demonstration/README.md and MEMORY_AND_SCOPE.md. Existing repair/bypass gameplay is session-only. Saving an editor level preserves authored placement; stopping Play resets gameplay. The old walkthrough does not demonstrate this new prop or all current native content.
- Historical textures, lights, companion and animation work exists. Reuse it; new Prop01 acceptance must name the actual current SDK, content and package tested.

Latest supplied visual review: codex-clipboard-384c91cc-1945-439d-9e14-1934c6b7b10f.png in the current chat. The overall capacitor silhouette, dark/gold casing and board markings are readable. Visible cleanup targets are the large triangular skirt below the board, ragged board edges, uneven casing/top rim and stretched or blurred label/seam regions. Inspect these in the raw mesh and UVs before choosing geometry edits or texture repainting; a screenshot alone cannot establish physical dimensions, manifoldness or final material response. Preserve this raw result and label the later comparison as cleaned/derived.

## Next three work packages after implementation resumes

| Package | Work | Evidence required |
| --- | --- | --- |
| A. Finish Prop01 | Preserve raw exports and source images. Make an editable cleaned master, establish authored dimensions and mounting pivot, and create an economical gameplay mesh. Review the source procedural model beside the reconstruction if available. Record which geometry was selected and why. | Front/back/left/right/top/underside and quarter previews, dimensions, bounds, topology/UV inspection, material slots, export inventory and provenance. |
| B. Bounded Unreal demonstration | Use the existing demo project and a copied playable level. Import into a new asset folder, set authored surfaces and simple collision, then place one inspectable example and a small repeated row. | Actual Unreal material appearance, normal orientation and silhouette, safe approach/jump/pass-by, saved placement after editor restart, one-versus-row cost and a screenshot. |
| C. Gameplay and native reuse | Attach the detailed visual to existing fault/relay semantics without changing reach or progression rules. Walk both demo routes and record a slow tour. Export the same accepted master through the current native pipeline, with its explicit collision/interaction definitions, then qualify in the native creator and saved chapter. | Both checked routes; native cook/admission/render/picking; Preview/Apply/Undo/Redo/Save; restart of a source-independent package with identical binding and transform. Unreal evidence cannot substitute for this native proof. |

A copied level, a saved editor asset, a working Play session and durable gameplay are four different outcomes. Persistent Unreal gameplay would be a separately scoped feature; the native opening already has its own persistence contracts to retain and verify.

## Asset authoring decisions

1. Preserve a raw master and cleaned editable .blend; never overwrite published packs or source references. Keep a direct procedural-source export for comparison when available. Cleanup is useful for the reconstruction workflow; the chosen game mesh must earn its place through appearance and measured cost.
2. Establish dimensions from the generator's stated design reference (13.6 mm PCB edge or 6.3 mm capacitor diameter) only after confirming that reference in the source. Label these as authored dimensions, not measurements of Brett's physical motherboard. An arbitrary factor of 0.1 is not a scale calibration.
3. Put the asset pivot at the mounting plane, center its placement footprint and document up/forward axes and units. Store any giant-world enlargement in the instance transform, separately from the source dimensions. Reuse the existing native-to-Unreal coordinate contract.
4. Remove unsupported skirt/floating fragments. Author unseen underside completion explicitly if needed; do not label it captured detail. Keep the silhouette smooth at the intended player distance.
5. Create a lighter gameplay mesh and compare its silhouette with the master. Profile a single close-up and the repeated row before fixing final triangle, texture and instance budgets. Retain the 4K source; choose the shipped resolution from visible detail and measured memory.
6. Author metal casing/contacts, dielectric PCB and plastic/base response as appropriate. Retain UV seams and tangent/normal conventions. Mark generated material maps as authored; verify color-space handling and the native renderer's supported material features.
7. Use explicit simple collision and stable interaction anchors. Visual detail or LOD replacement cannot silently add barriers, change repair reach or alter saved progress. Do not use the raw half-million-triangle reconstruction as an unqualified physics collider.

Asset record fields: stable asset UUID, content revision, source kind, source path/hash, source/license/provenance, units, dimensions, pivot/axes, export conversion, mesh/material/texture dependencies, cooked profile, bounds, instance transform, explicit collision binding, interaction role, measured load/residency/frame cost and known limits. This is an authoring checklist, not a new runtime schema introduced by this plan.

Retain v1 packs and existing callers. Reuse the implemented typed v2 mesh/character/audio paths and pinned importer subset after source verification. Preserve embedded cooked dependencies and project-owned copying through Preview, Save and isolated Play. Retain the approved modern-profile limits: 32 MiB mesh payload, 48 MiB audio payload and 128 MiB combined dependency closure, including decoded image, animation and GPU-residency accounting before publication. These limits are not permission to spend the whole budget on one prop.

## Opening spaces and state-dependent presentation

| Space | Asset purpose | State and interaction requirement |
| --- | --- | --- |
| Warm nook inside Jenison | Reserve-lit traces, controller, two-seat return point | Emergency warmth is available before restoration and does not complete shelter. Adam offers looking/turning guidance without forced memory playback. |
| Fault station | Hero capacitor, damaged connection, isolation device | Diagnosis, isolation, repair and reconnection are distinct. Live hazards are readable. Detailed scenery must preserve selection and walking space. |
| Bypass approach | Relay/connector sockets and cable/trace kit | Construction and commissioning are separate. Dismantling removes current bypass power; history still records what BS built. A valid return route remains. |
| Shelter/workbench | Claimed work area, seats, upgrade sockets, optional lamp | Physically entering shelter completes its own objective. Help/decline does not block the Pencil Room. Lighting follows actual supply conditions. |
| Pencil Room | Pencil, blank page, writing seat | Quiet optional remembrance, privacy and leaving/returning remain valid choices. New lines are authored dialogue, not recovered quotations. |
| Board horizon | CPU/RAM structures and distant RTX4090 FE-inspired landmark | Establish the larger hardware world while retaining the full RTX awakening as a separate later chapter requirement. Approximate geometry is not manufacturer CAD. |

Keep interaction prompts on the existing checked actions. A decorative capacitor needs no new mandatory quest. Adam can warn about live power, point to isolation, acknowledge a stable bypass, or offer a route back. Guidance is derived from current conditions and durable choices; no affection score, invented historical statement or automatic repair by Adam.

## Retained checkpoints 3-8 and their completion evidence

| Original checkpoint | Existing recorded foundation | Required current evidence before closure |
| --- | --- | --- |
| 3. Textured assets | Typed surfaces, AIBD3 placement/history/restart and historical CPU/GPU proofs | Exact current cook/import and native rendering; UV/tangent/color-space/seam/normal-transform checks; malformed/oversized/dependency-corrupt input and failed-replacement rollback; packaged closure without source paths. |
| 4. Lighting | Authored lights, exposure, bounded directional shadows and restoration readbacks | Current native reserve/main/bypass comparisons, linear-material and normal response, actual shadow GPU evidence and readable traversal. Power/light changes cannot invent shelter progress. |
| 5. Adam movement | Follow/Wait/Recall intent persistence, door-aware graph/trail and indexed animated rendering | Both first/third-person routes; closed-door waiting, validated Recall, rebuild/dismantle, depart/return, fall recovery, pause and new-process reload. Save valid intent/anchor, not footsteps/bones/frames. Movement does not reupload immutable scenery. |
| 6. Adam likeness | Bounded rig/import/playback and evolving v33 private study | User review of close-up/all-side/full-body previews and motion; naturalistic face/clothing with subtle depth-tested glow. Primary face anchor is the later-selected dark-jacket store photo. Preserve age labels on other references and the Pray for Kids band on the right wrist. Respect the 64-joint/four-weight contract; retain asymmetric/nonidentity skinning and all-clip GPU checks. Technical tests cannot approve likeness. |
| 7. Opening assembly | Diagnostic/personal stops, physical repair/bypass, shelter/Pencil and historical tours | Fresh source-independent native package, both coherent branches and alternate progression, normal saved chapter, optional NPC help and first-time human pacing. Target 8-12 minutes to shelter; further 20-30-minute chapter/Pencil/RTX expansion remains retained. Do not add filler or invented memories to reach a duration. |
| 8. Verification/delivery | Historical SDK consumers, releases, captures and incremental Drive restores | Complete current Debug/Release and required SDK consumers; ordinary packaged restart/creator/launcher acceptance; actual gameplay performance; current walkthrough/screenshots; compatible saves and final verified backup. Keep original failed evidence. Only then can full-goal completion be considered. |

Cross-cutting save gate: AIBD1/2 readers remain; edits to v3 content never downgrade its version or drop companion/light/media bindings. Preview, Undo/Redo, Save and a new process preserve identical bindings. Test missing dependencies and failed writes without changing old releases or real saves. Use isolated test worlds and explicit new compatible content/save branches where required.

Optional original audio retains the complete recording, its source sample rate and stereo channels, documented PCM conversion, and Play/Pause/Stop. The 62 draft cues still require listening review; the user's deferral is not caption approval. Keep new guidance authored text. Native video and synthetic voice remain later work. Private original media is not included in derived-art/software checkpoint uploads.

## Native qualification sequence when resumed

1. Reconcile current source against the retained freeze, inspect safe storage and classify any drift. Old session numbers in the paused handoff are not live-job evidence. Reuse an unchanged qualified profile only with explicit evidence; otherwise run a fresh consistent profile.
2. Finish current Debug suite and outstanding native camera/route cases. Retain original failed third-person evidence and its unknown cause. The prepared remaining-matrix helper is not ready until reviewed. Do not weaken reach, collision or reading guards to make a tour pass.
3. Qualify staged/relocated SDK consumers and prepare the current Studio candidate from the same source/content. Keep107 and held108/109.
4. Run the action matrix below in the packaged native chapter. Gather native GPU/readback evidence for actual texture, animation, light, shadow and hologram depth, alongside ordinary visible play.
5. Ask for first-time play feedback using an isolated fresh save; record actual completion time, time lost, mistakes and guidance clarity. Measure moving gameplay at1080p with optional inference off: frame-time distribution/long frames, CPU/process memory and GPU residency; target60FPS. A stationary FPS sample, scripted-time simulation or long documentary does not establish this result.
6. Finish likeness/presentation requirements and reviewed optional audio; rerun affected package checks. Record a slow walkthrough of both route alternatives with fresh sessions, readable stops and asset close-ups. Show the exact package/version; preserve the existing old recording.
7. Verify launcher delivery and final source/art/SDK/package checkpoint, including an authenticated restore. Update receipts and safely pause after delivery as requested. Do not mark the goal complete with any required gate missing.

## Action consistency matrix

| Action pair | Expected behavior and evidence |
| --- | --- |
| Open/close | Door power/latch/occupancy rules hold for BS and Adam; closing cannot trap the player or let Adam cross a blocked route. |
| Build/dismantle/rebuild | Current supply and visible geometry change together; cost/history obey existing rules; valid return and alternate progression remain. |
| Depart/return | Progress, ownership, hints and valid companion anchors agree; no duplicate reward or fabricated event. |
| Help/decline | Optional NPC/lamp outcome persists as declared; either choice can reach shelter/Pencil progression. |
| Follow/Wait/Recall | Follow respects doors; Wait survives reload at a valid anchor; explicit Recall validates nearby supported space and never moves BS. |
| Pause/fall/reload | Required clocks pause, recovery preserves choices, saving is acknowledged, and a fresh process reconstructs progression and movement intent. |
| Editor Preview/Apply/Undo/Redo/Save | Explicit dependency preview and commit semantics; no source path dependency or automatic publishing of isolated Play state. |
| Repair/bypass and camera modes | Both physical routes and first/third-person interactions pass without teleport/direct state manipulation being substituted for traversal. |

## Evidence, storage and backup

Each implementation package records changed paths, source/content versions, commands/results, actual screenshots/video, limits, resource measurements and next step. A separate plan update changes documentation freshness only; it does not make code/content qualification current or green.

Read-only local free-space observation during planning: C:258.09GiB and D:86.76GiB. The first Get-Volume query was denied CIM access; Get-PSDrive supplied these later observations. E: was not queried or used. Retain the existing C:/D: heavy-work policy after the E: incident; do not infer full hardware health from old capacity labels. Recheck before downloads/builds. No cleanup is authorized by this plan.

Use the existing Warm Beginning Workshop Drive collection and approved verified-project/derived-art scope. Keep raw scans, cleaned masters, runtime exports, source and evidence organized; exclude original family media, credentials, real saves and private Git/Master-ledger data. Upload only selected checkpoint files, verify destination/readback and restore before claiming backup completion. Cloud quota is unknown; record uploaded bytes rather than guessing remaining Drive capacity. No new cloud compute/service dependency is introduced.

This planning checkpoint's cloud copy contains this design document only. Canonical ledgers and monitor receive a bounded pointer/receipt; their prior source/test statuses remain intact.

## Exact next implementation step

When the creator requests implementation: open a disposable Blender copy of the raw Prop01/source model, compare front/side/underside geometry, confirm the authored reference dimension, and produce the first cleaned master and all-side preview. Do not repeat alignment/reconstruction merely to begin cleanup. Then execute work packages A-C and the retained native qualification gates above. While planning remains the instruction, extend only design/acceptance records.
