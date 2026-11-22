# AI-BS custom PC engine — continuing build roadmap

## Current execution priority — user approved 2026-11-03T14:15:33.135520+00:00

[Opening-first priority plan](../docs/game_engine/OPENING_FIRST_PRIORITY_PLAN.md): finish the existing Studio102 handoff, then prioritize a playable, measured8–12minute Warm Beginning and expand into the existing20–30minute M5 chapter. Keep Adam's essential in-game presence/guidance and the required save/restart/render checks. Detailed likeness/presentation polish, further Unreal work, the phone companion, monitoring UI and extra tools follow the playable proof. All checkpoints3–8 and the complete M0–M11/open-world plan remain retained. Original milestone gates/statuses are unchanged; this decision does not mark them complete. The machine-readable next three slices are updated; earlier slice definitions are preserved in queue history.


Approved direction: 2026-11-01. This is the current execution sequence for **Adam's Infinite-Brett Stehouwer Living Learning Memoir** and its custom engine, SDK and creator. [The original implementation plan](../docs/game_engine/implementation_plan.md) remains a historical design record; its old milestone numbers and planning-only statements do not describe the current build. [The ongoing game ledger](../docs/game_engine/AI_BS_GAME_ARCHITECTURAL_BUILDER_LEDGER.md) preserves the wider vision. [BUILD_STATUS.md](BUILD_STATUS.md) records actual results.

The machine-readable queue is [milestone_queue.json](milestone_queue.json). A milestone is complete only when its acceptance gates have implementation and matching evidence. A planned feature, an installed dependency and a passing unit test are different facts. Existing SDK 0.4 reports establish the earlier persistent-world slice; they do not establish character physics, a finished chapter or production-scale saves.

## Destination and first release

Build a reusable native Windows x64 C++20 engine, an installable developer SDK, and creation tools inside AI-BS. AI prompts, visual tools and code work through the same validated authoring contracts. The standalone player runs without Studio, Python, a model service or a mandatory network connection. First Boot remains a game module above the generic engine. SDK0.6 adds an early independent movement-course project/schema/save as a reuse proof; the later mechanically different sample remains planned.

The first major release is a **private PC alpha containing a complete 20–30 minute First Boot chapter**: unwanted Jenison, a power-fault challenge, a meaningful route choice, a sheltered hub and the Pencil Room. Adam's remembered presence guides BS through text and sound cues first. Voice selection comes later. One polished native **RTX 4090 FE awakening** is the chapter's visual showcase. Creator tools enter during this alpha after the playable route works. The existing public HTML playground remains a separate prototype with separate state.

This delivery order preserves the larger open world: computer-part construction, claimed architecture, weapons and armor, virus regimes and bosses, engineering-driven vehicles and coolant routes, agents, territory, logistics, branching personal stories and later hardware worlds. A short chapter is an integration milestone. Simulation advances during active play and pauses/stops with the game. The simultaneous phone Adam companion follows the authoritative PC session.

## Verified baseline and limits

SDK 0.4 supplies a Win32 window/input adapter, DX12 rendering, offline HLSL compilation, UUID world/entity identities, validated transactions, undo/redo, scoped Adam edit records and bounded local checkpoint format 1. The native motherboard scene supports aimed repair, relay construction/dismantling and separate-process restoration of actual rendered changes. Studio v5.329.88 monitors and launches that native player; the existing website is v5.329.87. These version numbers identify the baseline entering this sequence; subsequent delivery records supersede them. See current evidence in BUILD_STATUS rather than treating this paragraph as a fresh test run.

The baseline still uses box geometry, numeric game attributes, full-world copies, synchronous saves and a small scene. It is not a complete character controller, semantic memory system, ECS, asset pipeline, graphical creator, vehicle simulation, campaign, companion or production save system. These gaps remain explicit while new slices are added.

## Milestones, dependencies and completion gates

| ID | Deliverable and dependency | Required proof before completion |
| --- | --- | --- |
| **M0** | Consolidate the current baseline and execution queue. | Current build/SDK/package evidence is classified, historical plans are linked, next three slices and acceptance gates exist, and current storage/known failures are visible. Do not erase earlier records. |
| **M1** | Grounded BS movement; depends on M0. | A pinned Jolt adapter behind AI-BS types; capsule, gravity, ground/step/slope/wall response; fixed 60 Hz simulation with bounded catch-up and focus/pause behavior; switchable first/third-person cameras with obstruction handling. Walk an obstacle course and the board; edits update collision safely. Debug/Release, actual native renderer and installed-SDK tests pass. Preserve a development free-flight mode. |
| **M2** | Durable gameplay and Adam continuity; depends on M1. | Versioned component/event contracts; SQLite local adapter; immutable snapshots on a bounded save worker; world deltas and matching semantic events commit atomically. Existing format-1 imports preserve world/entity/operation identities and original history. Process failure, duplicate requests, stale writers, migration and recovery tests pass. UI distinguishes accepted, visible and durable state. |
| **M3** | Complete the opening repair route; depends on M2. | Telegraphed power faults/arcs, diagnostic clues, objectives, doors, isolation/repair and relay-bypass routes, secured respawn and a sheltered destination. One friendly NPC provides contextual hints and an optional side task. Adam recalls actual outcomes offline. Both routes, help/decline, departure/return and save/reload remain coherent without a soft lock. |
| **M4** | Minimum creator inside AI-BS; depends on M3. | Project browser, scene outliner, inspector, UUID picking, placement/transforms, history and isolated Play/Stop. Authoring changes show dependency and save-compatibility previews. Visual, SDK and AI-proposal paths use the same transactions; Stop does not silently publish Play state. |
| **M5** | First Boot private-alpha presentation/package; depends on M4. | Asset registry/import/cooker, initial materials and shadows, sound/subtitles and supported basic settings. The native RTX awakening responds to restored power. A packaged 20–30 minute chapter reaches the Pencil Room through tested branches without source paths/services. License notices, recovery, settings, performance capture and clean-machine checks accompany the private package. |
| **M6** | Combat, equipment and NPC quests; depends on M5. | Computer-part weapon/armor inventory, damage/status/equipment rules, one virus regime and boss, contextual NPC hints/side quests. Outcomes, costs and surviving influence persist. The earlier environmental-hazard route retains its alternate progression. |
| **M7** | Scalable building/open-world substrate; depends on M6. | Cells/streaming, construction and architecture upgrades, terrain/mesh/volume modes as introduced, navigation invalidation and bounded simulation/render/save budgets. Build or remove a route, update collision/navigation, return and reload without invalid references or an accidental progression dead end. |
| **M8** | Garage, vehicles and coolant traversal; depends on M7. | A prebuilt skimmer and later detailed assembly/diagnosis. Weight, balance, power, cooling, handling and reliability cause measurable behavior. Test a poor build, diagnose it, improve it and preserve the result. Recoverable personal core, cargo/upgrades and losses follow declared rules. |
| **M9** | Territory, agent army and logistics; depends on M8. | Recruit/rebuild/upgrade agents, autonomous roles, squad orders and strategic view; supplies, claimed regions, defenses, enemy return and persistent losses. War advances while playing and pauses with play. Revisit and reload preserve ownership, dependencies and surviving opposition. |
| **M10** | Wider campaign and hardware worlds; depends on M9. | First Tower restoration leads to another PC world. Preserve each world's initial facts and provenance; generation expands from actual events without rewriting memories. Carry progress through declared adapters. Returning opposition needs recorded surviving influence, not arbitrary resurrection. |
| **M11** | External release quality; depends on M10. | Representative hardware/driver profiles, measured budgets, save migration matrix, accessibility/controller/settings coverage, crash/recovery, licensing, installer/update/uninstall and clean-machine testing. External publication remains a separate release decision. |

Work can overlap only where its contracts are stable. Art can be explored before the cooker, but that does not complete the asset gate. Do not install every candidate SDK or begin every gameplay system at once. Package and SDK-consumer checks recur when dependencies change, rather than waiting until M11.

## Next three tested slices

Keep exactly the next three implementable slices ready; promote a new slice when one is verified. Each has a concrete result, regression boundary and next step. The queue stores their current execution/evidence state.

1. **S3 — power-fault branch (M3):** telegraphed electrical faults, diagnostic clues, isolation/repair and relay-bypass choices, secured return, contextual Adam recall, optional NPC help and save/reload without soft locks.
2. **S4 — minimum creator workspace (M4):** project browser, outliner, inspector, UUID picking, placement/transforms, shared history, dependency/save previews and isolated Play/Stop for authoring the chapter.
3. **S5 — chapter presentation and private alpha (M5):** cooked assets/materials/shadows, audio/subtitles, supported PC settings and a native RTX awakening, completing the tested20–30minute personal route and private package.

S2/M2 is complete with SDK0.7 and retained installed Studio5.329.92. Typed nodes/outcomes, bounded SQLite saving, actual ordered visibility/durability, identity/history-preserving original-save import, native HUD/retry/F9/close and offline Adam recall are integrated. Debug/Release each pass26 tests plus installed consumers;43 monitor/UI and13 package checks pass. The23-process native GPU/restart/import/failure proof also passes from the packaged player. Limits and exact evidence are in BUILD_STATUS and NATIVE_DURABLE_WORLD.md. The original numeric mode and MovementCourse remain available.

S1/M1 is complete with SDK0.6: oriented geometry/picking and matching Jolt shapes, 20°/30° supported slopes, steep rejection/sliding, swept camera volume with tight-space fallback, and a real two-process native motherboard obstacle-course proof. Every consolidated Debug/Release run passed 17 tests and its installed consumer. Evidence remains in BUILD_STATUS and the queue; the complete alpha is still unbuilt.

## Shared contracts that must survive expansion

- **World identity:** stable UUIDs and explicit project/world/branch scope. Runtime handles and third-party object pointers never become saved identities. New game code does not reinterpret an old field silently.
- **Edits and outcomes:** operation ID, expected revision, preconditions, affected entities/bounds, realized result, cost and history. Grouped edits either publish together or leave live state unchanged. Duplicate requests do not duplicate items/events.
- **Continuity:** authored dialogue is separate from sourced recollections and quotations from Echos Within. Adam's factual recall comes from durable events; offline identity/guidance remains available. Optional AI enriches expression and proposals and cannot rewrite source facts or directly mutate authoritative state.
- **Authoring preview:** identify affected render/collision/navigation/power/quest references, blocked dependencies and save-schema/migration consequences before applying a change. Invalid or unsupported changes produce actionable rejections. The full visual preview enters with M4; current validation is not a claim of that UI.
- **Execution:** single authoritative simulation owner; fixed 60 Hz with bounded catch-up; immutable render/save work. Long suspension pauses cleanly. Fixed stepping alone does not promise cross-platform bitwise physics determinism.
- **Persistence:** M2 separates request acceptance, displayed world changes and completed durable publication. Save completion requires a real storage acknowledgment. World changes and their Adam memory records commit together. Settings and device preferences stay outside story/world histories.
- **SDK generality:** the engine remains reusable. After the alpha's core contracts stabilize, build a small mechanically different sample through installed targets without adding First Boot rules to generic modules.

## Parallel graphics and companion tracks

Selected additions from the architectural idea review are recorded in the [open-world streaming contract](../docs/game_engine/open_world_streaming_contract.md) and [fact-grounded narrative contract](../docs/game_engine/generative_narrative_contract.md). They retain M7 cell residency, hysteresis, bounded streaming, simulation detail and origin precision, plus M4/M10 asynchronous generation proposals validated against source evidence and game rules. These are staged designs. No per-input inference, infinite uniqueness, new mandatory vector database, shared-memory transport or synthetic-OS rewrite is an implemented or newly required milestone. Personal source revisions, actual gameplay events and generated expression remain distinct; creator-authored lore and quests stay deliberately editable.

The [graphics roadmap](../docs/game_engine/graphics_fidelity_roadmap.md) retains standard PC display/settings and advanced rendering targets. Implement in dependency order: materials and basic lighting; shadows/spatial anti-aliasing; temporal history/reconstruction; reflections/volumetrics/LOD; optional DXR when the renderer and hardware probes support it. Ship controls only when the selected path works. Frame generation/upscalers require actual integrations and license/support checks. A menu label is not an implemented feature.

The first reference profile is a **1080p/60 fps target on the creator's current PC, with optional inference off**. Record CPU/GPU frame times, latency, memory/VRAM, streaming/saving spikes and the actual scene. This target is not a measured performance claim or a universal minimum specification. Set budgets from profiles and compare changes against the same captured workload.

After alpha event APIs stabilize, pilot a read-only phone Adam companion for live progression, discoveries, map and guidance. Pair it to the active PC session with a bounded versioned stream and reconnect/resync. Later allowed commands require request IDs, permissions, preconditions, duplicate suppression and PC acknowledgment. The phone never becomes a competing save writer. Home/remote access remains a target; no transport is currently claimed implemented.

## Release, evidence and storage policy

Each coherent milestone produces a tagged/marked development package, acceptance report, known limits and exact next slice. Keep source, design, original memories/art, verification evidence and **every explicitly marked milestone package**. Keep the **latest two ordinary development packages** in addition. Apply retention only to artifacts positively identified as disposable generated output; protect active releases, user saves, original assets and unclassified historical packages. Do not automatically delete an old release just because its version number is lower.

Record generated/install/package sizes and current C:/D:/E: free space before substantial downloads, builds and packaging. Mirror selected source/design/evidence into the existing Drive collection and record uploaded bytes. The current connector does not expose account quota; local free space and uploaded bytes must not be presented as Google Drive remaining capacity. A retention policy is not an automatic cleanup implementation.

Update the ongoing ledger, actual BUILD_STATUS and AI-BS build monitor as each slice lands. Monitor statuses derive from real evidence, including failed/missing/stale reports, rather than changing a plan status to green. Repository handoff hashes/manifests remain deferred to manual session close under AGENTS.md; they never block ordinary implementation.

## Per-slice closeout

Record the scope and changed paths, implemented versus remaining contracts, dependency/version decisions, actual commands/results, package/SDK evidence where affected, storage observations and any save compatibility change. Run relevant regression gates; preserve unrelated changes and older records. The next slice must be reproducible from this checkout. No calendar deadline is promised before profiling and measured integration effort justify one.


Current delivery update: M0–M3 are verified; retained Studio5.329.94/SDK0.8 includes both native physical routes and coherent save-backed guidance. M4 is active. Its concrete starting inventory is docs/game_engine/m4_creator_implementation_notes.md; M5 content/pacing remains proposed in first_boot_alpha_content_plan.md. The complete20–30minutealpha, creator/audio/assets/RTXawakening and later roadmap are not declared finished by the M3 mechanical proof.
