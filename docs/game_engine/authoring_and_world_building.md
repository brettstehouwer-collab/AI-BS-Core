# AI-BS authoring and world-building architecture

Planning date: 2026-10-31, America/New_York.
Status: PROPOSED implementation architecture; no editor, world-building system, SDK installation, successful build, or playable capability is claimed by this document.
User direction: combine AI prompting, visual editing, and code authoring; retain the full construction scope, including repairs, modular/freeform placement, terrain, voxels, procedural content, assets, and behaviors.
Release slices stage delivery; they do not remove capabilities from that intended product scope.
Read with [architecture specification](spec.md), [implementation plan](implementation_plan.md), and [component registry](component_contracts.json).
The registry remains authoritative for its proposed existing fields; new contracts here require future schemas and executable validation.

## 1. Product and project ownership

AI-BS is both the reusable creation engine and, in First Boot, the fictional world.
The engine owns runtime lifecycle, rendering, physics adapters, assets, scene identity, reflection, editor operations, and packaging.
A game project owns its rules, content, components, scripts, objectives, and player-facing construction permissions.
First Boot is the first game module and integration project; its setting and error-combat rules do not define every game.
AI-first creation includes generating and modifying scenes, layouts, assets, rules, and behaviors; it is broader than NPC dialogue or texture generation.
All three authoring routes operate on one authored project and the same runtime contracts.
Adam is the living continuity core connecting that architecture, the creator's intent and the evolving world. His identity, semantic memory and interpretation are engine infrastructure; First Boot supplies their particular relationship and expression. See [Adam core and First Boot](adam_core_and_first_boot.md).

The core includes Adam's reusable identity/continuity/interpretation architecture without fixing Jenison, memory-leak story rules, or First Boot's power mechanics into every project.
Keep firstboot.* components, action registrations, fault behaviors, progression, and repair semantics in the game module.
Generic command/event registries, scene queries, metadata, placement primitives, and resource services belong to reusable engine APIs.
A shared gameplay package may emerge from demonstrated reuse; naming a First Boot rule generic does not establish that reuse.
Initial game modules remain statically linked with the recorded toolchain; this does not introduce a public dynamic-plugin ABI.

## 2. Shared project model

Each project has a UUID, schema version, engine/API compatibility requirement, and explicit game-module entry.
Its manifest declares scenes, starting scene/spawn, asset roots, input actions, settings, build profiles, importer settings, and required modules.
Generated artifacts retain job/tool/model provenance, declared inputs/settings, and relevant seeds; provenance contains no credentials.
Project-relative references and stable asset/entity IDs replace developer-machine absolute paths.
Source scene/prefab/behavior documents are authoritative authoring data; cooked binaries are derived player inputs.
Caches are disposable and reconstructible from declared source inputs and tool versions.
Game saves store player progression and selected runtime overrides through SaveService; they do not replace authored scenes.
Authoring history belongs to project editing, separately from player checkpoint history.

~~~text
game_project/
  project.aibs.json        # Identity, schemas, modules, scenes, targets, settings
  game/                   # Project C++ sources and proposed later scripts
  scenes/                 # Authored scene documents
  prefabs/                # Prototypes and variant documents
  behaviors/              # Visual behavior source and supported script assets
  assets/source/          # Mesh, image, audio, animation, and other source assets
  generators/             # Versioned procedural definitions and retained outputs
  .aibs/staging/          # Candidate AI/import/build artifacts before admission
  .aibs/history/          # Recoverable authoring operations and undo data
  .aibs/cache/            # Disposable importer/cooker/build cache
  build/cooked/           # Derived runtime asset packages
  build/player/           # Assembled native player and declared content
~~~

Writable player saves live in the selected integrated or per-user store, outside source and cooked asset trees.
The manifest/schema/history formats above are new PROPOSED design contracts, not files produced by an existing engine.

## 3. One creation-operation contract

AI tools, viewport tools, inspectors, graphs, and project authoring APIs express scene changes through common typed operations.
Examples include CreateEntity, SetField, AddComponent, RemoveComponent, Reparent, InstantiatePrefab, PlaceInstance, and EditTerrainRegion.
Engine operations remain generic; project game commands translate repair, resource costs, or power-link intent into validated operations.
A creation envelope includes operation UUID/type/version, project and scene IDs, session epoch, base authored revision, targets, preconditions, parameters, and provenance.
Provenance identifies the human/tool/job origin and its declared inputs; the operation retains sufficient undo information.
One serialized authoring-document owner applies authored edits, manages history and persistence, and publishes document revisions. Use a shared native authoring library/host so the Qt UI, AI tools and SDK clients do not implement competing validators.
The edit viewport can share that native tool host; Play runs a separate snapshot and simulation owner. A running player is not required to save an authored document.
Runtime/game-world operations apply on the simulation owner at a safe boundary. Return distinct accepted, applied and durably committed states or a concrete rejection reason.
Workers prepare assets or region updates asynchronously and never mutate the live world directly.
A grouped scene edit validates its complete result before publishing it; failure leaves the previous authored state usable.
For retry-safe durable edits, commit the operation result and affected delta together. After a restart, return the recorded result for a retried committed operation; a command UUID alone does not establish exactly-once effects.
For large prepared resources, publish a new logical revision only after required render/physics consumers can adopt it safely.
Do not block a frame waiting for inference, compilation, import, disk writes, or terrain reconstruction.

Authored revisions change for authoring edits; simulation ticks and unrelated moving objects do not invalidate every pending authoring job.
Target-dependent preconditions still protect against deletion, replacement, incompatible state, or a changed session.
Code-authored scene generation uses these operations and schemas rather than bypassing identity/reference validation.
Game code may also issue runtime commands; those changes remain in the play world unless explicitly captured as authoring edits.

## 4. AI, visual, and code workflow

A creator can select an object/region/system and request a change, build it with visual tools, or author its implementation in code.
The common lifecycle is establish scope -> prepare candidate -> validate -> optionally preview -> apply -> inspect/play -> undo or continue.
Preview behavior is configurable by workspace/job policy; it is not a mandatory approval gate for every AI edit.
An automatic-apply policy may commit validated scoped scene changes and record their normal history.
An interactive policy can show proposed operations, affected entities/assets, differences, and a temporary scene preview.
Invalid output remains a failed candidate with useful diagnostics; it must not silently become accepted project data.
Cancellation discards unpublished candidates; undo is the explicit operation for already committed edits.
AI output must use supported contracts; requesting an unsupported feature produces an identified extension task rather than an invented success.

Scene changes and source-code changes have different publication mechanics.
Scene operations support atomic logical commit against the authored revision.
C++/script/file changes are staged as project-file differences, validated, built through the ordinary toolchain, and previewed in a compatible new runtime session.
Applying file changes uses recoverable file publication/history; compilation and GPU session publication have separate success/failure states from a scene transaction.
A failed candidate build leaves the previous usable player/editor session and published artifacts available.
Undoing source changes restores the relevant source revision and requires an appropriate rebuild; it does not rewind an external compiler process.
Generated code receives the same diagnostics and compatibility checks as manually written code.
There is no promise to round-trip arbitrary hand-written C++ into visual graphs.

## 5. Undo, redo, and Play sessions

Group related edits into named history entries; retain field values, entity mappings, source patches, or bounded terrain-region before-images as appropriate.
Redo replays the committed operation against its recorded prerequisites rather than asking a model to regenerate it.
New edits after undo create a new history branch or discard redo according to an explicit project policy.
External file edits are detected and reconciled into the project revision; stale undo records cannot blindly overwrite them.
History retention, compaction, and large terrain-edit limits are configurable and visible to the creator.
Version control remains useful independently; local undo history is not a claim of repository equivalence.

Play forks an isolated authored snapshot and selected save context into a separate runtime session.
Stop discards transient play-world changes and cancels or invalidates pending session-bound jobs.
Applying selected play changes back to the project is an explicit, validated authoring operation.
Player checkpoint writes target the selected play/save context; routine editor experimentation must not silently replace a chosen published save.
Each Play start/stop exercises process ownership and cleanup; a crash must leave authored project files recoverable.
Separate-window native playback comes first; embedded native surfaces remain conditional on the architecture's lifecycle tests.

## 6. Prefabs, variants, and identity

A prefab is an asset with its own UUID and prototype-local entity IDs.
An instance has a stable instance identity and an explicit mapping from prototype-local IDs to persistent scene entity UUIDs.
This mapping separates asset-local references from the project's instantiated entity identity domain.
Duplication creates new instance/entity UUIDs, remaps internal references, and preserves intentional external references.
Serialized world references never rely on memory offsets, entity names, or ECS storage indices.

The initial variant model has one explicit base, versioned field overrides, and an acyclic dependency graph.
Keep base values, variant overrides, instance overrides, and player-save overrides distinct.
Removing an override reveals the inherited value; writing that same inherited value is still a defined override operation.
Prefab updates preserve valid overrides and report deleted fields/entities, incompatible types, and unresolved references as conflicts.
Structural additions, removals, and reparenting require explicit versioned override operations rather than undocumented document merging.
Initial editing may start with field overrides; full structural variation remains in the intended later scope.
Nested prefabs require cycle detection and stable instance mapping before admission.
Prefab changes participate in ordinary validation, undo, cooking dependency invalidation, and scene migration.

## 7. Behavior authoring and code boundaries

Visual behavior graphs represent typed events, conditions, state, and actions through registered project/engine APIs.
The proposed first semantic target is a small event/condition/action model; its source format and executor require a versioned contract.
A graph's declared variables and save behavior use explicit types, defaults, identities, and migration rules.
Loops, event cascades, allocations, and per-tick work have enforceable execution budgets.
Invalid connections or missing command registrations fail validation before packaging.
Graph source is authoritative for graph-authored behavior; generated runtime data is derived.
Visual material and animation graphs are separate later authoring domains with their own cook/runtime contracts.

Native C++ supplies new components, engine extensions, performance-sensitive systems, and registered commands.
Lua is a PROPOSED later gameplay scripting option through the same API; its version, bindings, execution limits, and saved-state model remain unresolved.
Scripts and graphs receive explicit world/query/command capabilities, not unrestricted access to renderer internals or arbitrary engine pointers.
Editor tooling can create project files; in-game script capabilities remain governed by the game's rules.
Runtime code changes initially require rebuild/restart; hot reload is a separately validated extension.
The creator can combine graph behavior, scripts, and native systems without claiming automatic equivalence between their source representations.

## 8. Full construction and editable-world scope

The intended player-facing toolkit includes repairing existing objects, replacing parts, and restoring connected systems.
It includes modular kits with grids, sockets, snapping, rotation, placement previews, removal, and project-defined support rules.
It also includes free placement of objects and assemblies, with project-defined scale/overlap/attachment constraints.
Terrain tools include raising/lowering, flattening, smoothing, painting, cutting, filling, and carving volumetric space.
Freeform mesh authoring additionally requires explicit vertex/edge/face edits, UV/material bindings, validation and collision recooking; free placement and terrain brushes alone do not fulfill that capability.
Procedural tools include seeded terrain/layout/structure generation and retained artist/player modifications.
AI can propose assets, structures, terrain edits, recipes, systems, and behaviors through the same staged authoring interfaces.
A request for new executable behavior uses the code/build workflow; an in-game generation feature only accesses capabilities the project exposes.
Construction recipes, inventories, costs, ownership, damage, support, and interaction reach are game-rule schemas rather than universal engine assumptions.

Editor freedom and player permission use a shared operation substrate with different policy layers.
The editor may place objects without inventory costs or progression restrictions while retaining schema, reference, and resource validation.
Player commands validate the active game's ownership, resources, reach, collision, terrain restrictions, and progression before publishing changes.
The same geometry operation can therefore succeed in the editor and be rejected meaningfully during play.
Game rules control what runtime AI or procedural agents may construct; the editor's authority is not implicitly inherited.

The PROPOSED world representation combines heightfields for suitable surface terrain, sparse volumetric regions for caves/cuts, and ordinary mesh instances.
These are cooperating source representations; choosing them does not promise a completed voxel renderer or a particular meshing algorithm.

| Representation | Intended use | Required edit result |
| --- | --- | --- |
| Prefab/modular instances | Structures, machines, connected parts, reusable assemblies | Stable placement/attachment identity, game policy, undo and saved creation/deletion |
| Editable mesh objects | Freeform authored objects and mesh terrain | Source topology/attributes, derived render mesh and valid collision |
| Heightfield surface | Broad outdoor ground and surface sculpting | Versioned height/material edits with local render/collision rebuilds |
| Sparse volumetric region | Caves, overhangs, tunnels and excavatable ground | Declared scalar-field semantics, meshing/seams/LOD, collision and persistent edits |

Heightfield surfaces alone cannot represent arbitrary caves/overhangs; NVIDIA's terrain chapter motivates volumetric source data for those forms and distinguishes a generic density field from a true signed-distance field. The hybrid choice above is an AI-BS design recommendation, not a supplied terrain implementation. [Primary terrain reference](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu).
Each editable region has stable identity, source revision, spatial bounds, dependencies, and persisted edit data.
Render meshes, collision, navigation where supported, and material data are derived consumers with explicit invalidation.
Region rebuilds run asynchronously; publish compatible logical geometry/collision revisions together instead of exposing unintended temporary holes.
Jolt documents controlled heightfield shape updates and warns against editing concurrently queried collision data. Prepare replacement collision data and publish it at the declared boundary; movable construction pieces initially use supported primitive/convex/compound shapes. [Heightfield source contract](https://github.com/jrouwe/JoltPhysics/blob/master/Jolt/Physics/Collision/Shape/HeightFieldShape.h), [dynamic mesh limitations](https://github.com/jrouwe/JoltPhysics/blob/master/Docs/Architecture.md#dynamic-mesh-shapes).
Navigation is a separate consumer. Recast's tiled meshes support regional rebakes; temporary obstacle updates do not by themselves add a new walkable bridge or excavated passage. Keep affected tiles unavailable until the correct geometry revision is admitted. Recast/Detour is a researched provider candidate, not an installed module. [Recast overview](https://github.com/recastnavigation/recastnavigation), [TileCache interface](https://github.com/recastnavigation/recastnavigation/blob/main/DetourTileCache/Include/DetourTileCache.h).
Undo and saves retain actual edits or sufficient versioned deltas; a generation seed alone does not preserve arbitrary modifications.
Streaming owns cell residency, cross-cell references, edit ownership, pending jobs, and unload/reload behavior.
Project-defined limits bound edit size, generated entities, job queues, memory, and per-frame uploads; overload handling remains visible and recoverable.
The editable-world acceptance route includes building a bridge, walking over it, admitting updated NPC routing, removing it, saving/reloading, and repeating a tunnel edit across region boundaries. Record geometry/collision/navigation versions and queue/memory measurements rather than certifying only the visible brush effect.

## 9. Creator workspaces and lifecycle

Project Home handles create/open, templates, compatibility, settings, and build profiles.
World provides viewport/outliner/inspector, selection, transforms, prefab placement, modular tools, and later terrain/volume brushes.
Logic connects behavior graphs, scripts, native source, typed API discovery, and navigation to diagnostics.
AI Workshop provides scoped prompts, selected context, job/cancel status, optional previews, provenance, and history navigation. Adam connects requested sector/asset/code work to verified project history and actual job outcomes, framing restoration without hiding technical diagnostics.
Asset Lab handles imports, source/cooked status, materials, audio, and later animation and generation tools.
Play/Debug provides isolated sessions, game/simulation diagnostics, resource budgets, and save-context selection.
Build/Release validates references and schemas, cooks declared inputs, assembles packages, and reports reproducible outputs.
These can be workspaces inside the existing native studio rather than separate applications; no browser surface is required.
Selection, project revision, diagnostics, and job state remain coherent when moving among workspaces.
The complete creator lifecycle is new project -> author/import -> validate -> Play -> revise -> cook/package -> launch exported player.

## 10. Proposed release slices and acceptance

| Release | Scope staged for delivery | Required proof |
| --- | --- | --- |
| R0 Foundation | Toolchain, native player, renderer, identity/reflection, Adam continuity contracts and basic scene/assets pipeline. | Package a native sandbox and round-trip a validated scene using recorded build inputs. |
| R1 Playable | First Boot repair chain, movement, audio/UI, objectives, saves and native Adam continuity/memory/expression. | Complete repair/save/reopen and accurate offline recall in the independent player; First Boot rules reside in its module. |
| R2 Creation alpha | All three authoring routes, shared history, scoped AI edits, visual/code workflow, basic modular placement and prefabs. | Make the same scene edit through AI, visual tools, and code; undo it; author/package two distinct small games without engine-source edits. |
| R3 Editable streamed worlds | Freeform construction, heightfield sculpting, volumetric edits, procedural generation, streamed ownership and persisted modifications. | Build, carve, cross a cell boundary, save, reload, and preserve geometry/collision/progression without unbounded resource growth. |
| R4 General engine beta | Expanded AI-generated systems/behaviors, scripting, structural prefab workflows, material/animation graphs, richer construction and scaled content. | Reusable projects mix the creation paths and extended systems, validate/build independently, and meet declared package/resource budgets. |

R0-R4 are product capability slices; M0-M7 in the implementation plan remain engineering dependencies and need explicit reconciliation when scheduling.
A capability is not complete because its UI exists: its authored representation, runtime behavior, undo/save policy, and packaged-player behavior must agree.
The two-game proof should use First Boot plus a different small rule set, such as a timed collection/puzzle course, with separately registered project components/actions.
Neither game should require modifying core renderer/world/editor sources to express its ordinary rules.
The second game may use primitive art; it proves creator reuse rather than visual polish.

## 11. Next data-contract families

These are proposed future descriptors, not additions to the implemented field registry. Define their types, defaults, constraints, storage and migrations before implementing corresponding tools.

| Contract | Fields to settle | Ownership/persistence |
| --- | --- | --- |
| ProjectDefinition | project UUID, format/API versions, game module, scene/asset roots, input actions, build profiles | Authored project data |
| PrefabInstance | prefab UUID/version, instance UUID, prototype-to-entity map, base/variant/instance overrides | Authored plus declared player overrides |
| PlacementPolicy | grid/snap units, socket kinds, orientation rules, bounds, support/overlap policy, game validation hook | Authored recipe/policy, evaluated by editor or game context |
| ConstructedEntity | persistent UUID, source prefab/recipe, owning cell, attachments, game owner, creation operation | Player world creation record; deletion uses tombstones |
| EditableMeshSource | source topology/attribute version, material/UV bindings, edit history, derived mesh/collision versions | Source content plus saved modifications; GPU resources derived |
| TerrainRegion | cell/region UUID, heightfield/volume kind, bounds/resolution, source/generator revision, materials, edit references | Large source/deltas outside checkpoint blobs with durable references |
| GenerationArtifact | producer/tool/model version, declared input/settings/seed, artifact IDs, source provenance, validation state | Staged/published project content and versioned metadata |
| NavigationRegion | tile key/bounds, agent profile, input geometry revision, rebuild generation, ready/dirty state | Cooked or regenerable derived data; preserve authoritative world source |
| AuthoringOperation | operation UUID/type/version, actor/job, expected revision, target IDs/bounds, preconditions, inverse/delta reference, result state | Recoverable history/journal with durable deduplication |
| StructuralGroup | member/connection IDs, support/damage policy, break thresholds, physics representation | Authored rules plus saved broken/support changes; fidelity remains a game decision |

The game can use default policies while the SDK allows replacing them. A field is not implicitly saved because an inspector displays it; scene/save/derived ownership remains explicit.

## 12. Unresolved design work

Define project/scene/prefab/graph schemas, migration ownership, and executable validators before implementing their editors.
Select graph execution semantics and whether Lua enters the first scripting release; record API capabilities and resource limits.
Choose terrain resolution, sparse-volume layout, mesher, region boundaries, seam handling, and collision/navigation rebuild strategy through measured prototypes.
Define construction recipe/support/ownership schemas, large-edit history retention, external-editor conflict handling, and cross-cell operation recovery.
Define generated-asset provenance/licensing fields and the supported import/rig/material/animation subsets.
Set automatic-apply defaults, preview ergonomics, diagnostics, and history retention as product policies; no pending topic is recorded as user approval.
Research references and exact dependency choices remain in the linked implementation/dependency planning; this document does not substitute for those checks.
No builds, installations, source-module changes, database migrations, or runtime tests are performed by this planning document.
