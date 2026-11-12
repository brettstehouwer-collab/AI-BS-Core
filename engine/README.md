# Current native opening build status — Studio106 / SDK0.17.0

Studio5.329.106 is the installed engineering preview; all five existing launchers were verified. New openings use the v20surface Adam study; existing projects keep their owned assets and saves. SDK0.17.0 Release/Debug are published under D:/AI-BS-Game-Resources/SDK/0.17.0. Full registered engine baseline128tests/config, relocated SDK9consumers/config, source discovery35cases and affected packaging134cases retain their exact evidence scopes. Frozen creator/saved-play, both bundled opening routes/restarts and a fresh1080p walkthrough passed;67Asource/art/evidence/video backup was raw-restored and every member checked.

The full8–12minute Warm Beginning goal is unfinished: naturalistic likeness/refinement, caption listening review, first-time human pacing/current gameplay performance and final acceptance remain pending. See docs/game_engine/STUDIO106_SURFACE_PREVIEW.md and out/warm_beginning/monitor_summary.json. Entries below are historical.

# AI-BS native PC engine / SDK0.11

LATEST — Studio5.329.98 /SDK0.11 is verified and deployed through the five existing Studio shortcuts. It adds bounded character import/cooking, textured indexed characters, full creator dependency export and persistent Adam model bindings. Both configurations passed91native+2installedSDK tests;232Python/Qt tests and335broaderStudio tests passed. Actual frozen creator/assets/placement/reopen checks passed. Adam likeness and the full Warm Beginning opening remain in progress. Checkpoint09: https://drive.google.com/file/d/1ChgCGu7qPCVObE9VHOmCu5HGXpwb5hOL/view?usp=drivesdk


LATEST — Revision 0.24: Studio 5.329.97 / SDK 0.10 delivers persistent visual motherboard-part placement in Chapter creator: project-owned immutable mesh/license/provenance packs, native Preview/Apply, typed transforms, Undo/Redo, Save and restart. Separate frozen create/reopen processes preserved every field and saved byte; actual native viewport/picking/isolated Play passed. Debug and Release each passed 59 tests; both installed SDK consumers passed; 183 Python/Qt and 68 packaging tests passed. All five existing launchers were backed up and now open97. S5BP is complete; S5B textures/lighting and the wider M5 alpha remain in progress. Studio96/95, SDK0.9/0.8, public87, original memoir/photos, real saves and separate Unreal remain preserved.
Guides: engine/PERSISTENT_PLACEMENT.md and engine/CREATOR_QUICKSTART.md. Checkpoint: https://drive.google.com/drive/folders/12tZrIZmt1mQtyd3Tt_OeAAE-gJoWTG5k
Earlier entries are historical.

LATEST — Revision0.23: Studio5.329.96 /SDK0.9 delivers the first native asset/material pipeline and Assets workspace. Cook triangulatedOBJ with explicit base-color/emission materials and license; inspect immutable cooked packs and preview detailed parts in the motherboard scene. Self-authored reference4788triangles/8materials rendered with0GPUdebugerrors. Debug55/55,Release55/55,bothinstalledSDKconsumers1/1,167Python/Qt and51packaging tests passed; actualfrozenworkflow and5launcherreadbacks verified. This completes S5A, not allM5: persistent chapter asset bindings,textures/PBR,lighting/shadows/audio/settings and personalalpha remain next. Studio95/SDK0.8 retained;public87 unchanged.
Guide: engine/ASSET_PIPELINE.md. Checkpoint: https://drive.google.com/drive/folders/1eSw3hsqo6sbqolVJq_B6Vq7E1mfuIT7q
Earlier entries are historical.

LATEST — Revision0.22: Studio5.329.95 creator and local AI field authoring are VERIFIED and deployed through all five existing launchers. Frozen editing, native DX12 preview, explicit Preview/Apply/Save, history and isolated Play passed. One actual installed Qwen field request passed; model/request scope remains limited. M5 personal alpha/assets/audio/settings/RTX awakening remain unfinished. SDK0.8.0 and previous releases preserved; public87 unchanged.
Quickstart: engine/CREATOR_QUICKSTART.md. Checkpoint: https://drive.google.com/drive/folders/1x0ellJ3c3TsbzWjPOql2yTA67lXb5ewj
Earlier entries are historical.

**Adam's Infinite-Brett Stehouwer Living Learning Memoir**

The custom Windows x64 C++20 engine now connects stable saved entities and Adam history to an interactive native DX12 motherboard scene. The native PC game remains the main experience. Adam's simultaneous phone companion is a future secondary progress/guidance client, with the PC authoritative for world changes and saves.

The retained installed M3 release is Studio5.329.94 / SDK0.8, with explicit additive registry migration, versioned mechanism/quest outcomes and the playable chapter route. Rebuild C++ clients for the expanded public variant; binary ABI compatibility is not asserted. The complete20–30minutealpha and creator remain under development. See [concept intake](ARCHITECTURE_CONCEPT_INTAKE.md) for selected architectural ideas and deferred work.

## Build and verify

Requires Visual Studio 2022 C++ Build Tools and Windows SDK, Python, and the Python `cmake` package (CMake 3.25+). CMake fetches immutable SHA-256-checked Jolt 5.6.0 and SQLite 3.54.1 source on first configuration. Jolt uses the x64 SSE2 baseline. Both dependencies are static and their notices install with the SDK. Consult BUILD_STATUS for the retained installed Studio version; packages include their matching native player and notices. `bcrypt` supplies OS-random UUID entropy. Run from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Debug
powershell.exe -NoProfile -ExecutionPolicy Bypass -File engine/scripts/verify.ps1 -Configuration Release
python -m unittest discover -s engine/tests -p 'test_*.py'
```

Verification builds the configured engine/demo/scene/gameplay/physics/checkpoint tests, installs the SDK, and configures/builds/tests a separate consumer against that installation. Every failed command stops the script. Generated output remains in ignored `out/` and `install/` directories. Evidence is in [BUILD_STATUS.md](BUILD_STATUS.md).

## Save and restart the headless First Boot demonstration

The parent save directory must already exist. From the repository root after building:

```powershell
New-Item -ItemType Directory -Force engine/out/checkpoints | Out-Null
& engine/out/windows-msvc/Debug/aibs_player.exe --checkpoint engine/out/checkpoints/first-boot-demo.aibs
& engine/out/windows-msvc/Debug/aibs_player.exe --inspect engine/out/checkpoints/first-boot-demo.aibs
```

The first command creates/repairs a core node and publishes a checkpoint. Repeating it retries the original commands without duplicating changes. The second launches a separate process and reads the saved IDs, capacity and Adam events without applying edits. Running without arguments remains an in-memory demonstration. These are console integration examples, not a graphical game or a complete power-network simulation.

## Monitor progress inside AI-BS

In the native Studio source build, open **Engineering & Specialized Labs → AI-BS Game Engine Build**, or use Ctrl+K. The view refreshes every three seconds while visible through the existing worker bus. It shows build stages/results, logs, recent source/design changes, recorded restart/recovery checks, checkpoint sizes, generated/install byte totals and C:/D:/E: free space. Missing/malformed evidence never implies success. Source changes after verification mark it stale.

Build observations live in `out/build_progress.json`; restart-test evidence is in `out/checkpoint_verification.json`. The latest log is `out/verification.log`. The verification script excludes overlapping builds and retains at most 100 progress events. Storage scans are bounded and include orphan temporary files in generated-byte totals. The monitor is read-only. Retained Studio v5.329.92 packages the current game workspace, original/course modes and new durable world; the last published website snapshot remains v5.329.87. Google Drive account quota is not exposed by the connector/local monitor.

## Installed source SDK

| CMake target | Responsibility |
| --- | --- |
| `AIBS::Core` | Fixed 60 Hz accounting and OS-random UUID v4 allocation |
| `AIBS::World` | World/entity value data and finite numeric field constraints |
| `AIBS::Authoring` | Validated grouped edits, revisions, undo/redo, isolated Play copies and realized Adam change records |
| `AIBS::Persistence` | Versioned bounded checkpoints, corruption checks, full-state validation and guarded publication |
| `AIBS::Platform` | Native Windows window, input, focus and resize/minimize lifecycle |
| `AIBS::Render` | DX12 device, swapchain, depth, motherboard geometry, camera and GPU readback |
| `AIBS::Scene` | Immutable UUID-bearing oriented boxes, matching mesh/normals and exact oriented ray picking |
| `AIBS::Physics` | Jolt capsule, rotated static box collisions, fixed 60 Hz stepping and swept camera spheres |
| `AIBS::Player` | Grounded BS controller, first/third-person cameras, focus pause and explicit inspection flight |
| `AIBS::FirstBoot` | Sample game schema, seeded motherboard, repair/build/dismantle rules and guidance |
| `AIBS::DurableFirstBoot` | Separate sample-game target: typed nodes, true outcomes, tombstones, placement and offline recall |
| `AIBS::MovementCourse` | Independent persisted motherboard obstacle-course game module |
| `AIBS::Gameplay` | Versioned typed components/events and bounded immutable admission/acknowledgements |
| `AIBS::GameplayCodec` | Canonical bounded binary component/event encoding |
| `AIBS::GameplayStore` | Scoped SQLite atomic state/events/receipts, recovery and history |
| `AIBS::GameplayWorker` | Bounded background saving and actual commit completions |
| `AIBS::GameplayWorld` | Prepared immutable world changes, save reservation and ordered visibility/durability |
| `AIBS::LegacyImport` | Original format-1 preservation and typed baseline import |
| `AIBS::Engine` | Generic SDK aggregate; FirstBoot remains a separately linked sample game module |

Use `find_package(AIBS 0.7 CONFIG REQUIRED)` and `target_link_libraries(game PRIVATE AIBS::Engine)`. See [examples/sdk_consumer](examples/sdk_consumer). Match MSVC toolchain and Debug/Release configuration. Version 0.2 adds public data fields and a target; rebuild clients. There is no stable binary plugin ABI or pre-0.2 native checkpoint format to migrate.

## World identity, commands and Adam continuity

`Entity.id` remains an authored alias for convenience. `persistent_id` is the UUID authority; a world also owns its own UUID. Recreating a deleted alias allocates a new UUID. Retired UUIDs cannot be recycled. Optional UUID targets on SetField/Erase reject commands aimed at the wrong incarnation.

Transactions have an operation ID, expected revision, grouped edits and optional description. Accepted changes preserve the original request receipt for exact retry matching, alongside realized UUID-bearing memory evidence. Undo/redo restores the original identities and records its resulting changes. Play copies never publish to the authored session automatically.

CheckpointStore saves world state, numeric schema, retired identities, Adam event evidence/descriptions, accepted receipts and undo/redo together. Loading stages and validates the entire snapshot before publishing it to the live session. Project/branch/schema mismatch fails explicitly. An existing slot checks world identity and previous checkpoint head, so a stale session cannot overwrite newer progress. An accepted edit remains in memory until a save succeeds. The native First Boot application attempts a checkpoint after each successful world edit; the low-level SDK does not autosave implicitly. This old CheckpointStore API is synchronous and single-owner. The separate SDK0.7 durable-world mode now uses its bounded SQLite worker and actual commit acknowledgements.

Adam's current journal records actual admitted edits/history with project, branch, world, revision, operation, UUID-bearing effects and supplied meaning. It is not yet the full quest/hazard/route memory system. Demo dialogue is authored game dialogue. See [SAVE_FORMAT.md](SAVE_FORMAT.md) for format, validation and tested recovery boundaries.

## Limits and next build

This remains a small-scene prototype using whole-world/history copies. Sessions are single-thread-owned; unsaved in-session histories are unbounded. Checkpoints are capped at 16 MiB, strings at 4,096 bytes, collections at 10,000 entries, decoded entity/field expansion at 200,000 units, and replay at 200,000 work units plus a 64 MiB estimated-copy budget. Applied groups remain capped at 1,024 edits. UUID identity is implemented; generation-checked runtime handles and the full planned component catalog remain future work. Registered typed component/event contracts are implemented in SDK0.7.

The native window/DX12 prototype is implemented and verified. The rotated static-box/capsule and slope physics slice is implemented. Dynamic rigid bodies, audio, asset cooker, world streaming, visual editor, networking and phone app remain unimplemented. Persistent scene mapping and first interactions now work. M1 slope/camera/course coverage is complete. M2 durable gameplay is complete; M3’s power-fault route is next; see [BUILD_ROADMAP.md](BUILD_ROADMAP.md) and [milestone_queue.json](milestone_queue.json). The broader target remains in the [architectural builder ledger](../docs/game_engine/AI_BS_GAME_ARCHITECTURAL_BUILDER_LEDGER.md).

## Optional Concept Playground

The supplied [First Boot concept playground](../docs/game_engine/concept_playground/first_boot_playground.html) has a dedicated launch button in the BS Game build workspace. It opens in the external default browser and requires Internet for the supplied Three.js renderer. Use right-drag or arrows to look, WASD to move, and E/left click to interact. All values are simulated; reloading resets it. It does not use native checkpoints or replace the custom PC engine. Hosted and packaged browser rendering and controls passed real Chromium checks, including right-drag look and direct scene interaction. See its [notes](../docs/game_engine/concept_playground/README.md).

## Native motherboard world

Launch **AI-BS → Engineering & Specialized Labs → AI-BS Game Engine Build → Launch native motherboard world (PC / DX12)**. See BUILD_STATUS for the installed Studio package; verified shortcut updates retain the original links. The installed source SDK also supplies `engine/install/release/bin/aibs_motherboard.exe`.

Controls: **WASD/arrows** move, **right-drag** look, **Space** jump, **Shift** sprint, **V** first/third-person camera, **F2** developer inspection flight (Space/Ctrl rise/lower there), **E/left click** interact, **B** place a relay where you aim on the board, **Delete** dismantle a relay, **Ctrl+Z/Y** undo/redo, **F5** retry saving, **F9** reload, **Esc** close. This is a grounded PC world-building prototype with a native status panel, collision and target feedback. Inspection flight freezes BS in place while moving only the camera. The geometry is an authored/generated motherboard layout with CPU socket, RAM towers, storage fins, traces and an illuminated GPU landmark. It is not a measured CAD replica or a completed game.

The renderer now extracts immutable snapshots from CreatorSession. Repairs update core/GPU/trace illumination, relays can be created/removed, and world changes plus Adam records reload together. Player/camera position and transient inspection are not saved. Restart and F9 select a clear entrance on the actual motherboard; a blocked entrance uses a bounded fallback grid without deleting or moving user constructions. The entire grid being obstructed produces an explicit recovery error. The existing save/identity tests still pass independently. See [RENDER_SLICE.md](RENDER_SLICE.md) for SDK boundaries and exact verification.

The public [BS Game hub](https://ai-bs-dashboard.web.app/?tab=bs_game) uses normal workspace login. The [browser playground](https://ai-bs-dashboard.web.app/bs-game/index.html) is public and separate from native game saves. The current native package bundles its local renderer assets rather than relying on a remote CDN.

## Current world save and restart

Run `engine/install/release/bin/aibs_motherboard.exe` or use the native launcher in AI-BS. By default the game creates/restores `%LOCALAPPDATA%/AI-BS/FirstBootWorld/native-world.aibs`. It uses project `first-boot-world`, branch `main`, and the First Boot numeric schema. This is separate from the older headless example save; existing user checkpoints are never reset or migrated silently.

Use `--checkpoint PATH` to choose another slot. The first launch seeds 56 persistent entities. Existing slots are loaded, not reseeded; invalid format, scope, schema, game data or render budget leaves the previous session/checkpoint intact or stops initial loading with an error. Game-specific validation runs before load publication. The initial motherboard cannot be dismantled/undone through these game controls; constructed relays can.

Successful repair/build/dismantle/undo/redo attempts an atomic checkpoint and refreshes the GPU mesh. The panel keeps **UNSAVED** visible if saving fails, including during later inspection. Press F5 to retry. The last committed checkpoint remains safe; unsaved edits are still lost if you exit before a successful retry. These sentences describe the original format1 mode. The separate SDK0.7 durable mode now provides background saving, retry and deferred close; broader recovery UI remains later work.

The real-process GPU acceptance test creates a world, repairs and builds, restarts, undoes/redoes across restarts, dismantles, and restarts again. Captured pixels differ after edits and match exactly after successful reload. The test also proves invalid mesh replacement retains pixels, empty scene clearing works, and bootstrap undo is rejected. Results are shown in the AI-BS build monitor from `out/world_scene_verification.json`.

Full build path: [BUILD_ROADMAP.md](BUILD_ROADMAP.md). Detailed status: [BUILD_STATUS.md](BUILD_STATUS.md). The original longer [implementation plan](../docs/game_engine/implementation_plan.md) remains a planning record; current verification lives in the ongoing ledger and these build records.

Your standard PC display and advanced graphics targets are recorded in [graphics_fidelity_roadmap.md](../docs/game_engine/graphics_fidelity_roadmap.md). It separates the current raster prototype from future materials/shadows/AO/AA/upscaling/RT/HDR/post-processing and display settings. Those features are planned, not implemented toggles.

## Grounded movement and verified M1 scope

See [PHYSICS_SLICE.md](PHYSICS_SLICE.md) for the pinned dependency, player/collision contracts, actual GPU evidence and supported slope/camera boundaries. The build workspace now reads the twelve-milestone queue separately from verification reports, and shows movement results from `out/movement_verification.json`. An incomplete gate remains unverified even when other tests pass. Format-1 world/Adam checkpoints remain unchanged.


## M1 movement course / SDK0.6

The independent motherboard course now verifies steps, true slopes, walls, falls, focus and real-process save/restart. Launch the installed player with `--obstacle-course`, or use the new course button in the native build workspace in Studio v5.329.91 and later. It uses `%LOCALAPPDATA%/AI-BS/MovementCourse/native-course.aibs`, project movement-course/main, and never loads the personal FirstBoot save. WASD/arrows walk, right-drag looks, Space jumps, Shift sprints, V changes view, E/left-click repairs the relay core, F5 saves and F9 reloads/returns. Authored source quaternions drive matching render, picking and collision geometry. See MOVEMENT_COURSE.md for the actual proof and limitations.

SDK0.7 adds the typed canonical codec, atomic SQLite store, bounded asynchronous worker, prepared gameplay world and non-destructive original-save importer. The separate --durable-world mode now uses them; the original native CheckpointStore mode remains available unchanged. See GAMEPLAY_CONTRACT.md and BUILD_STATUS.md for actual verification and remaining integration. SDK clients rebuild against0.7; original FirstBoot schemas and format1 checkpoint bytes remain compatible.

Small context-continuity snapshots and their verified Drive links are kept in `docs/game_engine/checkpoints/INDEX.md`. Larger milestone archives stay in the established Core Engine Architecture folder. This is checkpointed development, not a completed private alpha.

Selected future concepts are recorded in the [open-world streaming contract](../docs/game_engine/open_world_streaming_contract.md) and [fact-grounded narrative contract](../docs/game_engine/generative_narrative_contract.md). Both distinguish proposals from implemented runtime features.


## Native durable First Boot / SDK0.7

Use the dedicated **Launch durable First Boot world (PC / DX12)** button or run `engine/install/release/bin/aibs_motherboard.exe --durable-world`. It has its own SQLite database at `%LOCALAPPDATA%/AI-BS/FirstBootDurableWorld/world.sqlite`; it does not reset or silently import the original `.aibs` save. Repairs/builds/dismantles publish typed deltas and matching actual outcomes, save on a bounded worker, and recall only acknowledged durable events. The HUD shows SAVING, UNSAVED/RETRY and SAVED separately from visible revisions. F5 retries; F9 waits for a successful save; close drains pending work while preserving live retry.

Detailed controls, explicit original-save import, scopes, failure behavior, SDK game target and actual proof boundaries: [NATIVE_DURABLE_WORLD.md](NATIVE_DURABLE_WORLD.md). This remains a motherboard construction prototype. SDK0.8 adds the chapter development mode described below; creator tools and the cinematic RTX awakening remain later milestones.


## First Boot chapter development / SDK0.8

After building the current source, run `engine/out/windows-msvc/Release/aibs_motherboard.exe --durable-world --chapter`, or use **Play First Boot chapter** in the source Studio workspace. Studio94/SDK0.8 includes this verified mechanical route; older Studio92/SDK0.7 does not support it. The launcher admits chapter mode only from a known player path with an adjacent supported `aibs_capabilities.json`; that marker describes an available mode, not passing M3 proof.

The chapter has a separate default save at `%LOCALAPPDATA%/AI-BS/FirstBootChapter/world.sqlite`. Existing M2 databases require an explicitly selected `--world-db PATH --upgrade-chapter`; unsupported layouts reject before registry changes. An upgraded format2 database cannot be opened by the old Studio92 player. Original `.aibs` import remains explicit into a new target path.

WASD/right-drag/Space/V control BS. E operates the aimed fault, isolation switch, socket, door, NPC or lamp; B builds and Delete dismantles relays. Ctrl+Y offers help and Ctrl+Z declines nearby optional help. F2 inspection pauses chapter actions/hazards. F5 retries failed saving and F9 restores saved state. Door/collision, true outcomes, current versus committed memory, resource staging and save acknowledgements use the same authoritative world boundary.

See [FIRST_BOOT_CHAPTER.md](FIRST_BOOT_CHAPTER.md) for current component/layout/power contracts and verification limits. Core/module/continuous movement proofs are separate from native process/HUD/GPU proof, packaged deployment and the complete personal alpha. Consult BUILD_STATUS for actual current results.


Current typed chapter integration: [CHAPTER_PLAY](CHAPTER_PLAY.md). Revision0.20
verifies native typed preview and isolated Play; earlier generic viewport limits
and historical counts above remain scoped to their original checkpoints. Live
AI generation and the complete personal alpha are still unfinished.


Revision0.21 source creator includes [live local AI field proposals](AI_AUTHORING.md).
Choose an installed local model and selected object, describe a change, inspect
the native before/after preview, then explicitly Apply and Save. One actual Qwen
request and155 Python/Qt tests are verified. Other models can make mistakes;
validation/review remain required. Retained Studio94 does not yet include this
source UI; the next step is packaging/deployment, then the complete personal alpha.
