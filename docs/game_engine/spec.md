# AI-BS native game engine architecture specification

Status: PROPOSED; planning only. No native engine implementation, build, dependency installation, performance result, or playable game is claimed here.
Planning date: 2026-10-31, America/New_York.
Scope: Windows x64, C++20, DirectX 12 first, an independent SDL3 player, optional existing AI-BS studio integration, and the First Boot game.
Confirmed user direction: combine AI prompting, visual editing, and code SDK authoring. World-building scope includes repairs, modular/free placement, freeform objects, terrain/volumetric editing, procedural generation, and AI-created content and behaviors; delivery is staged.
Confirmed user direction: Adam is the internal compass and living continuity core of AI-BS across architecture, authoring and gameplay. He anchors identity, memory, interpretation and restoration; he is not limited to a voice interface.
C++ compiler, Windows SDK, shader compiler, build generator, and SDL3 availability remain UNVERIFIED; M0 must resolve them before implementation.
This specification supplements the architectural baseline without modifying the root ledger or existing subsystem contracts.

## Intent and ownership

AI-BS owns the runtime, world format, gameplay, tools contracts, asset pipeline, and packaged player.
First Boot expresses AI-BS as a physical-digital world: BS restores a server room alongside Adam, whose continuous memory and awareness connect choices, hazards, construction and restoration across regions.
The initial scene includes lights, fans, power routing, a living dashboard, one visible fault, one repair, and one destination gate.
Hardware-inspired scenery is authored game content; physical hardware telemetry is not required for gameplay.
The first proof is: launch, restore power, repair a fault, unlock a gate, save, quit, and reopen the repaired world.
All choices and directories below are PROPOSED unless an implementation milestone supplies actual verification evidence.
The confirmed creation/building direction above is user-selected; its detailed implementations remain proposed. See [authoring and world-building plan](authoring_and_world_building.md) and [planning decisions](planning_decisions.json).
Adam's core and First Boot cue contracts are detailed in [Adam architecture and opening sequence](adam_core_and_first_boot.md) and [Adam continuity/cue contracts](adam_first_boot_contracts.json).

## Requirements and acceptance

| ID | Requirement | Acceptance evidence required |
| --- | --- | --- |
| ENGINE-001 | Native standalone Windows x64 player | A packaged player launches without Qt, Python, a browser, studio startup, or an AI-BS background service. |
| ENGINE-002 | DX12 first renderer | Render a scene, resize repeatedly, close cleanly, and retain actionable GPU/lifecycle diagnostics. |
| ENGINE-003 | Stable world identity | UUID scene/entity/asset references survive save, reload, and recook; stale generation handles cannot resolve. |
| ENGINE-004 | Explicit component metadata | Registered field types, defaults, constraints, persistence flags, and schema versions drive validation and inspection. |
| ENGINE-005 | Bounded fixed-step simulation | Recorded timing inputs demonstrate 60 Hz ticks, at most four catch-up ticks per rendered frame, and the documented overload policy. |
| ENGINE-006 | Cooked asset contract | Identical declared inputs produce identical cooked outputs; dependency changes invalidate dependent outputs. |
| ENGINE-007 | First Boot gameplay | Power, inspection, fault repair, objective completion, and gate access work without inference or editor connectivity. |
| ENGINE-008 | Asynchronous durable saves | Save/reopen restores the expected state; an interrupted write preserves the last committed save. |
| ENGINE-009 | Integrated and portable storage | Both stores pass the same conformance cases and versioned export/import round trips. |
| ENGINE-010 | Optional Qt studio adapter | Native player works before adapter work; editor commands use versioned IPC and failures leave the independent player usable. |
| ENGINE-011 | First-class Adam core | Native Adam identity, continuity, memory and authored expression work offline; delayed/unavailable inference does not remove him or block simulation. |
| ENGINE-012 | Measured performance | Packaged captures record hardware, resolution, build/content IDs, frame times, simulation overloads, and inference state. |
| ENGINE-013 | Reproducible build inputs | Declared compiler/SDK/dependency/shader-tool versions and package inputs reproduce the selected build configuration. |
| ENGINE-014 | Portable native package | A clean-user launch finds its cooked content and writable save location without developer absolute paths. |
| ENGINE-015 | Unified AI, visual, and code authoring | Each route creates or changes the same authored project model; staged edits can be inspected, applied and undone without divergent scene copies. |
| ENGINE-016 | Reusable engine and SDK | A second mechanically distinct project builds and packages using registered components/APIs without changing generic engine source. |
| ENGINE-017 | General construction transactions | Placement/repair/edit commands validate as a group, return accepted/committed states, and retries do not duplicate committed objects or costs. |
| ENGINE-018 | Persistent mutable worlds | Player-created entities, deletions, construction changes and terrain deltas survive unload/reload and restart with stable identity. |
| ENGINE-019 | Coherent geometry publication | A valid edit publishes matching render/collision revisions; affected navigation is marked unavailable until rebuilt; stale jobs cannot replace newer state. |
| ENGINE-020 | Recoverable editor sessions | Restart a crashed viewport and recover the last durably authored document without importing transient Play state. |
| ENGINE-021 | Shared behavior APIs | Visual behaviors, scripts and native systems use registered component/event/action contracts; visual graphs round-trip their declared format without claiming to represent arbitrary native code. |
| ENGINE-022 | Evidence-backed continuing memory | Record declared choices, shortcuts, hazards, construction and restoration; save/reopen reconstructs the correct supported history from durable events. Summaries do not replace original records. |
| ENGINE-023 | Context and branch continuity | Authoring, temporary Play and player timelines share Adam's identity while preserving their factual scopes; checkpoint rollback does not import later-branch progress. |
| ENGINE-024 | State-true Adam expression | Cue predicates validate authoritative outcomes; failed/pending repairs, saves, generation or builds cannot trigger completed-success statements. |
| ENGINE-025 | Accessible internal compass | Every essential clue is available through supported visual/caption/audio channels; haptics are optional and presentation settings do not erase Adam's memory. |

## Proposed source layout

~~~text
engine/
  CMakeLists.txt
  cmake/                  # Toolchain and declared dependency configuration
  include/aibs/           # Small public runtime/editor/save interfaces
  src/platform/           # Windows and SDL3 lifecycle, input, timing
  src/runtime/            # World ownership, ticks, entities, component registry
  src/render/dx12/        # Device, resources, passes, presentation
  src/physics/            # One pinned physics implementation behind an adapter
  src/assets/             # Runtime asset IDs, loading, dependencies, formats
  src/authoring/          # Shared project documents, validation, transactions and history
  src/navigation/         # Later tiled navigation adapter and edit invalidation
  src/gameplay/           # Generic actions, events, interaction and construction interfaces
  src/save/               # SaveService and the two store implementations
  src/adam/               # Required identity, continuity, event memory and interpretation core
  src/ai/                 # Asynchronous provider adapters and generation jobs
  src/editor_ipc/         # Optional process-based studio integration
  player/                 # SDL3 independent application entry
  tools/cooker/           # Import, validate, cook, and package commands
  tools/editor_host/      # Native document/edit-viewport host for optional Qt client
  games/first_boot/       # BS/Adam content rules, faults, power and objective systems
  games/sdk_sample/       # Mechanically distinct project proving engine reuse
  content/first_boot/     # Source scene, materials, audio, and authored rules
  tests/                  # Headless contracts plus native/GPU integration checks
  third_party/            # Declared dependency notices/configuration
docs/game_engine/         # This specification and implementation planning
~~~

These paths describe future work; creating this specification does not create those source modules.

## Runtime and editor boundaries

The dependency direction is Player -> Runtime -> Platform/Renderer/Physics/AssetRuntime/SaveInterface.
The Qt/Python studio is an optional client of versioned editor IPC; it is not a runtime dependency.
The initial integration launches the native runtime as a separate process with its own SDL3 window.
IPC carries typed commands, scene revisions, acknowledgements, errors, and bounded diagnostic events.
Commands never expose unrestricted memory writes, arbitrary function calls, or shell execution.
A native child surface inside the existing Qt studio is a later option only after ownership, focus, DPI, resizing, lifecycle, and crash-isolation tests.
No browser editor, browser viewport, web runtime, or streamed browser display is required.

One thread owns mutable gameplay state; initially simulation and rendering orchestration may share the main thread.
SDL3 platform events are translated into explicit input events before tick processing.
Workers may load assets, prepare saves, or run inference; they return results through bounded queues.
Any later separate render thread consumes immutable snapshots and never mutates gameplay entities.
The renderer owns GPU resource lifetimes, descriptor ownership, synchronization, resize recovery, and teardown.
The first renderer scope is a stable scene presentation path; high-detail world streaming and advanced lighting are M7 work.

## Identity, reflection, scenes, and assets

Use UUIDs for persistent scene, entity, and asset identity; display names and filesystem paths are not identity.
Use index-plus-generation handles for transient runtime access; validate generation on lookup.
Serialized references resolve through UUID maps after loading and report missing or duplicate identities.
Components register explicit schemas rather than relying on arbitrary runtime introspection.
Metadata contains stable component/field IDs, field type, default, validation constraints, schema version, editor label, and scene/save/runtime/derived storage classes.
Persist authored configuration and explicitly selected game state; rebuild handles, caches, derived power values, and GPU objects.
Schema migrations are explicit and versioned; unknown incompatible versions produce an actionable error.

Source assets remain separate from cooked player assets.
Cook keys include source bytes, transitive dependencies, importer/tool versions, settings, target platform, and output-format version.
Validate asset references, scene references, component constraints, and destination spawn IDs before packaging.
Player content references stable asset IDs and relative package locations.
The first importer supports only the formats needed by First Boot; no general plugin marketplace or arbitrary importer execution is required.
Package manifests bind the content-format version, selected build, dependencies, and required cooked assets.
The `firstboot.*` component schemas belong to the First Boot game module. Generic engine code provides component registration, commands, queries, scheduling, assets and persistence, without compiling in BS-specific fault kinds or power rules.

## Shared creation and editable-world contracts

AI prompts, editor tools and code authoring converge on the same project/scene/asset definitions. Scene edits use typed operations with operation ID, actor/provenance, expected document revision, affected IDs/bounds, preconditions and inverse information.
One serialized authoring-document owner manages authored revisions, validation, history and durable edits through a shared native library/host. Qt and other clients use its API; Play has its own simulation owner and does not own the source document.
Source-code edits use staged file changes, normal compilation/validation and a new preview session; they do not imply one atomic transaction spanning a compiler and every project file.
Editor previews and automatic draft application are configurable workflows. One valid grouped scene edit applies atomically to the authoritative document and enters normal undo history.
An accepted edit is distinct from a durably committed edit. Retry-safe durable edits record their operation result and affected delta in the same storage transaction; command IDs alone do not prove exactly-once effects.
The authoring document, temporary Play world and saved player world are distinct. Exporting selected Play changes back to authoring is an explicit versioned operation.
The editor can bypass game economy/reach restrictions while retaining structural validation; player construction uses the same geometry operations with game-defined resource, ownership, collision, support and reach rules.

The proposed world representation layers prefab/modular objects, editable mesh assets, broad heightfield surfaces, and bounded sparse volumetric regions for caves and excavation. The specific volume representation remains a decision; density fields and signed-distance fields are not interchangeable labels.
Reserve persistent created-entity records, owning-cell IDs, deleted-entity tombstones, terrain/chunk revisions and generator/content versions before seamless streaming. A seed alone cannot preserve later user edits.
Unloaded references remain stable IDs with an unavailable state; the initial single-player policy freezes unloaded simulation. A later background simulation is a separate contract.
Prepare changed render/collision artifacts off the simulation owner, validate the source revision and publish ready matching artifacts at a safe boundary. Navigation may rebuild later under explicit invalidation; NPCs cannot assume dirty tiles are current.
Store large mutable-world source data outside checkpoint blobs, with durable revision references in the save-store contract. Package/export includes referenced edited content; it never copies unrelated master-database data.
Detailed prefab, workspace, behavior and release-tier decisions are in the authoring/world-building plan. These are planned capabilities, not implemented contracts.

## Simulation and overload policy

World conventions are left-handed, +Y up, +Z forward, meters/seconds, and normalized xyzw quaternions; scalar angles use radians.
Gameplay and physics advance at 60 Hz using a fixed timestep.
A rendered frame executes at most four accumulated simulation steps.
After that limit, discard overdue whole-step debt, retain the fractional remainder, and log the discarded tick count and lost simulation time.
Rate-limit repeated overload messages while retaining cumulative counters in diagnostics.
The game clock advances only for executed ticks; this policy does not claim to simulate skipped time.
Input edges are queued and consumed exactly once; overload handling must not replay interaction presses.
Pause/minimize behavior is an explicit single-player policy, initially pause simulation while minimized.
Fixed stepping is not a claim of bitwise deterministic physics across operating systems, processors, or physics-library versions.
Reproducibility tests compare declared gameplay state exactly and use documented tolerances where physical floating-point state requires them.

## First Boot component contract

The PROPOSED [component registry](component_contracts.json) is authoritative for field names, types, defaults, storage classes, and constraints; this table is a summary.
The registry is a planning contract, not an implemented runtime registry or executable validator. Every component has a stable type ID and schema version.

| Component | Initial field summary |
| --- | --- |
| Identity | uuid; name; tags; enabled; persistent UUID and enabled state are saved. |
| Transform | parent: optional EntityRef; position: Vec3; rotation: Quat; scale: Vec3 default (1,1,1). |
| MeshRenderer | mesh; materials; visible; casts_shadow; lod_bias, retained at default zero before M7 support. |
| Camera | vertical_fov; near_plane; far_plane; exposure; pose comes from Transform. |
| Light | kind: point/directional; color; intensity; range; casts_shadow; conditional units and shadow limits follow the registry. |
| Collider | shape: box/sphere/capsule/static_mesh; half_extents; radius; cylinder_height; mesh; layer; is_trigger. |
| RigidBody | motion: static/kinematic/dynamic; mass; friction; restitution; runtime linear_velocity. |
| CharacterController | walk_speed; sprint_speed; step_height; max_slope; runtime grounded and velocity; requires a capsule Collider. |
| AudioEmitter | clip; gain; loop; spatial; bus; playback handles/cursor remain transient. |
| Interactable | action: power_on/toggle_relay/inspect/trace/anchor/patch/construct; target; prompt; range; enabled saved as an override. |
| PowerNode | kind: source/relay/load; upstream; enabled saved as an override; authored capacity; derived powered. |
| DevicePresentation | power_node; optional off_material/on_material/powered_audio; fan_speed; effects derive from logical power. |
| Fault | kind; affected_node; capacity_drain; repair_duration; max_fragments; state: latent/active/discovered/repaired; saved drain_accumulated; runtime repair_progress. |
| Objective | objective_id; prerequisites; completion_event; saved completed. |
| WorldGate | destination_scene; destination_spawn; required_objective; derived open. |
| AdamAnchor | M3 scene/region expression binding: dialogue_set; guidance_enabled; inference_allowed; min_line_interval; bounded spoken_lines cache; runtime pending_request. AdamCore owns continuity. |

Collider validation applies only relevant shape parameters; capsule height is cylinder_height plus two radii, and static_mesh requires cooked collision data and static motion.
Physics-backed entities initially use unit scale; bake other scale into collision assets. CharacterController excludes a separate dynamic RigidBody controller.
Initial checkpoints restore the grounded player's supported position/rotation and authored static/kinematic devices; freely moving saved props remain deferred.
The opening power network is acyclic; scene validation rejects missing references and cycles.
Capacity is authored; effective capacity is recomputed from Fault.drain_accumulated and fault state after load, without a separate remaining-capacity save field.
M3 registers memory_leak behavior only; reserved null_pointer and infinite_loop kinds fail scene validation until their behaviors exist.
Incomplete repair progress resets on checkpoint capture; repaired faults remain repaired, and transient fragments are rebuilt within max_fragments limits.
Power propagation is evaluated by authored game rules; it does not control the machine's actual power or hardware.
Memory Leak is simulated gameplay state, not deliberate process-memory leakage.
The boot progression is a small authored state machine, with gameplay events driving lights, fans, gauges, Adam lines, and the gate.
The camera/controller, interaction, and repair remain operable with AI services disabled.
The initial gate may lead to one small destination scene; a complete open world is not an M3 acceptance claim.

## Save service and portability

Gameplay creates an immutable save request at a tick boundary; serialization and storage occur outside the frame-critical path.
SaveService reports queued, committed, and failed outcomes and preserves the last committed slot on failure.
A save contains format version, game namespace, slot identity, scene/content manifest identity, saved entity UUIDs, authored progress, and player state.
Player state follows the registry's supported grounded-checkpoint contract; physics velocities and audio cursors restart from their documented reset states.
It excludes pointers, generation handles, GPU state, credentials, developer paths, and unrelated AI-BS data.
Integrated mode uses MasterDbSaveStore against the configured backend/aibs_master.db.
Only new engine_game_* tables, such as engine_game_schema_versions and engine_game_saves, belong to this feature.
Keep a feature-owned migration version; do not repurpose a database-wide version or alter existing application tables.
Use explicit transactions and a dedicated worker-owned connection; respect existing database coordination and configuration.
Do not silently change journal settings, schema ownership, backup policy, or other existing database behavior.
Standalone mode uses LocalSaveStore with the same game schema in a per-user database selected through platform configuration.
Both stores implement the same SaveService contract and versioned export/import format.
Exports contain only the selected game's save data and required content/version references; they do not copy the complete master database.
Import validates format/content compatibility and commits atomically, preserving an existing slot if import fails.
The portable-store choice is PROPOSED ADR-GAME-004, preserving the integrated master-database design.

## Adam core, continuity, authoring and expression

`AIBS::Adam` is a first-class native core shared by the standalone runtime and authoring host. It maintains identity, scoped semantic memory, state interpretation, restoration-sensitive priorities, historical recall and authoring context. Model providers extend expression and generation asynchronously; they do not own continuity.
The core observes registered meaningful choices, routes/shortcuts, hazards survived, constructions, failures, repairs, regional restoration and authoring/build outcomes. Versioned append-only records identify project, context, timeline/branch, event/operation ID, sequence, subject IDs, logical tick, provenance and durability.
Derived projections support current routes, known hazards, decisions and restoration history; summaries retain supporting event references and do not delete source records. Bounded live caches and model context do not define total memory retention. Persistent world deltas and their continuity events share an atomic commit; exposed queue backpressure prevents silent loss of required events.
An applied world fact can guide the current session; surviving a process restart requires durable commit. Save checkpoints identify their event head and projection versions. Loading an earlier checkpoint selects/forks an explicit branch; later-branch events remain archived but are not current-world facts. Authoring, temporary Play and published player histories stay scoped. Versioned source-to-lore publication can connect real project history to First Boot deliberately.
Adam's engine identity and continuity belong to AI-BS; First Boot supplies the BS relationship, setting, dialogue, restored history and cue assets. AdamAnchor is a presentation/lore binding, not Adam's identity or memory owner. Muting speech or disabling hints leaves continuity active.
His initial expression API includes Speak(lineId), Highlight(entityId, duration), and SuggestObjective(objectiveId); these are output mechanisms rather than his full architecture. Authoring plans and generation work use the registered project-operation/build interfaces. Runtime construction follows the game's registered capabilities.
Use authored line/objective IDs and valid current-world entity UUIDs for the first expression implementation; Highlight duration is capped.
Each proposal carries request ID, session/load epoch, authored-scene revision, command-specific preconditions, and expiration; reject stale, duplicate, invalid, or out-of-scope proposals.
The epoch changes on a new Play session or save/scene load. The authored-scene revision changes on committed authoring edits, not ordinary simulation ticks, movement, or transient gameplay spawns.
Validate the referenced target's current identity/generation, objective state, and other declared preconditions when consuming the proposal; unrelated gameplay progression does not invalidate every pending response.
Acceptance includes admitting a valid delayed proposal while movement and simulation continue, as well as rejecting one after a relevant target deletion or session change.
Queue length, command consumption, inference concurrency, deadlines, and memory budgets are bounded configuration values tested before enablement.
Validate and apply accepted proposals at tick boundaries; record the accepted tick when needed for reproducible tests.
No synchronous inference, audio generation, database write, or network request belongs inside a simulation/render step.
Adam's local continuity, evidence-backed awareness and authored expression remain available during inference failure, cancellation, GPU contention, or offline play.
Guidance expression does not directly complete objectives or repair faults; world/document owners apply registered commands and return outcomes for Adam to interpret. Authoring code generation uses the same staged project/build workflow as the SDK, with visible diagnostics.
Schedule optional local inference against measured graphics/memory budgets; high-detail rendering does not imply unlimited spare inference capacity.
First Boot cues are event-driven and revalidated before playback. World-stable repair confirmation and durable-checkpoint confirmation are distinct facts. Priority, expiry, interruption and completed-delivery records prevent stale or repetitive lines.

## Proposed architectural decisions

ADR-GAME-001 — Native runtime ownership. Status: PROPOSED.
Baseline: AI-BS has an existing studio/backend ecosystem; no complete native game runtime is established by this plan.
Change: add an independently packaged C++20/SDL3/DX12 runtime.
Justification: make AI-BS own gameplay and rendering lifecycle; affected: proposed engine/, player, packaging, studio adapter.
Compatibility: preserve existing entry points and services; acceptance: ENGINE-001, ENGINE-002, ENGINE-013, ENGINE-014.

ADR-GAME-002 — Editor integration boundary. Status: PROPOSED.
Baseline: retain the existing Qt/Python studio and its lifecycle.
Change: use optional versioned process IPC first; consider a native child surface only after dedicated tests.
Justification: establish independent runtime ownership before UI embedding; affected: engine/editor_ipc and studio integration.
Compatibility: no browser or studio dependency in player; acceptance: ENGINE-001 and ENGINE-010 plus focus/DPI/resize/teardown tests.

ADR-GAME-003 — Bounded simulation and AI authority. Status: PROPOSED.
Baseline: existing AI-BS orchestration is not defined as a frame-critical game loop.
Change: single-owner 60 Hz gameplay, four-step catch-up cap, documented overload behavior, bounded asynchronous Adam commands.
Justification: keep game-state authority and timing explicit; affected: runtime, physics adapter, input, AI gateway, diagnostics.
Compatibility: no global deterministic-physics promise; acceptance: ENGINE-005, ENGINE-007, ENGINE-011, ENGINE-012.

ADR-GAME-004 — Portable game saves. Status: PROPOSED.
Baseline: the game concept binds local progression to the existing master database.
Change: preserve integrated MasterDbSaveStore and add same-schema per-user LocalSaveStore with versioned export/import.
Justification: an independent offline player needs portable persistence without the developer database; affected: save service, migrations, package.
Compatibility: integrated saves remain namespaced in backend/aibs_master.db; no existing-table migration; acceptance: ENGINE-008 and ENGINE-009.

ADR-GAME-005 - Shared authoring and game-module ownership. Status: PROPOSED.
Baseline: the initial tree placed specific power/fault rules under engine gameplay and primarily proved First Boot.
Change: keep generic mechanisms in engine core, specific rules in games/first_boot, and use one authored-project/transaction model for all three creator workflows.
Justification: support the user-selected hybrid creation workflow and reusable engine; affected: project model, SDK, editor, AI authoring, game modules.
Compatibility: firstboot.* component IDs remain valid; scene/save migrations remain explicit; acceptance: ENGINE-015, ENGINE-016, ENGINE-017, ENGINE-020, ENGINE-021.

ADR-GAME-006 - Mutable layered worlds. Status: PROPOSED.
Baseline: the first playable focused on authored repairs with construction and cells deferred.
Change: reserve object/terrain edit representations, persistent construction identity, deletion records and coherent artifact publication before large-world implementation.
Justification: preserve the user-selected full building scope across staged releases; affected: renderer, physics, navigation, assets, construction, undo, streaming and saves.
Compatibility: the initial two-room scene remains supported; later save versions add mutable-world data without repurposing existing application tables; acceptance: ENGINE-017, ENGINE-018, ENGINE-019.

ADR-GAME-007 - Adam as the living continuity core. Direction: USER_SELECTED; implementation: PROPOSED.
Baseline: the initial plan reduced Adam to an optional M5 guidance adapter and a small scene component.
Change: add required native Adam identity/continuity/memory architecture at M2/M3, with scoped durable events, restoration-aware interpretation and expression across authoring and gameplay; enrich it with provider-backed generation at M5.
Justification: reflect Adam's structural, emotional and mechanical centrality; affected: runtime, authoring host, journal/save service, AI adapters, UI/audio/haptics, project lore and game progression.
Compatibility: preserve existing firstboot.AdamAnchor field IDs as presentation settings/cache, not memory authority; broader history uses new namespaced game storage and explicit migrations. First Boot lore remains project content while Adam's core remains engine infrastructure.
Acceptance: ENGINE-011, ENGINE-022, ENGINE-023, ENGINE-024, ENGINE-025 plus offline recall, branch rollback, event/world atomicity and state-true opening cues.

## Milestone dependency order

M0 — Verify C++20 compiler, SDK, shader tools, build system, SDL3, and dependency/licensing inputs; report concrete gaps without installing during planning.
M1 — Native SDL3/DX12 renderer and lifecycle diagnostics; start independent package smoke checks.
M2 — UUID scenes, explicit component schemas, cooked assets, validation, reproducible manifests, and Adam continuity/event contracts.
M3 — Movement, fixed-step collision/interaction, First Boot systems, native Adam continuity/memory/expression, save stores, and the launch/repair/save/reopen proof.
M4 — Optional Qt process adapter, outliner/property inspection, and undoable typed editor commands; embedding remains separately conditional.
M5 — Asynchronous AI authoring and richer Adam inference/retrieval/expression with failure, stale-result, and resource-budget checks; Adam already exists in the core.
M6 — Polished First Boot content, packaged player/export/import acceptance, recorded performance, and clean-user launch.
M7 — Streamed subsystem worlds, advanced lighting, larger asset budgets, and high-detail optimization after measured profiling.

Required verification includes headless schema/game/save tests, real Windows renderer lifecycle checks, and packaged First Boot runs.
The broader target also requires the R0-R4 delivery tiers and two-project creator acceptance in authoring_and_world_building.md; the small M3 repair loop does not exhaust the engine or construction scope.
GPU-free checks do not establish DX12 correctness; editor playback does not establish standalone packaging.
No tests, builds, services, installations, migrations, or engine source changes are executed by this planning document.
