# Game systems coverage review

Reviewed 2026-11-01, America/New_York, against the deployed Studio 5.329.97 / native SDK 0.10 records. The user's breakdown is a coverage checklist, not a request to replace the established architecture. Persistent visual asset placement is now verified, including native rendering, two-process frozen restart and exact project dependency ownership. The full personal alpha remains in progress.

**Legend:** ✅ verified within the stated existing slice; ◐ partial; ☐ planned. A checkmark does not mean the entire category is production complete. Evidence: `engine/out/persistent_placement_verification.json`, `engine/out/asset_pipeline_verification.json`, earlier chapter/save/movement proofs, and their actual test logs. The complete personal First Boot alpha remains unfinished.

| Area from the review | Coverage | What exists | What remains / milestone |
| --- | --- | --- | --- |
| Engine / hardware execution | ✅ native Windows PC foundation | C++20 SDK, Win32 window/input, actual DX12 rendering on the RTX 4090, pinned physics/storage dependencies and independently built SDK consumers | Broader hardware qualification, profiling, clean-machine/private-alpha delivery; cross-platform compilation is not implemented |
| Game loop / time | ✅ bounded simulation slice | Fixed-step simulation separated from presentation, bounded catch-up, pause/focus handling and native movement tests | Measured frame budgets as content grows; no guaranteed frame rate or cross-machine bitwise determinism claim |
| Systems design | ◐ | Power faults, repair/isolation versus relay bypass, doors, shelter, return routes and state-dependent outcomes | Equipment, combat balance, economy, vehicles and wider construction systems — M6/M7 and later |
| Level design | ◐ | Playable motherboard blockout and mechanical Jenison-to-hub/Pencil progression, collision-tested routes and alternate power progression | Full personal 20–30 minute pacing, encounter layouts, assembled environments and chapter playtesting — M5 |
| Narrative / quests / Adam | ◐ | Authored contextual Adam guidance, remembered outcomes, basic NPC help/decline and chapter branches | More verified memoir adaptations, dialogue/quest authoring, factions and richer outcome coverage; generated prose stays a draft |
| UI / UX | ◐ | Native build monitor, numeric and typed creators, outliner/inspector, Preview/Apply, history, Save/reopen, local AI panel and Assets tab | Persistent visual placement is verified; accessible game menus, inventory, broader settings and polished feedback still need implementation/testing |
| Gameplay programming | ✅ current mechanical slice | Grounded movement, first/third-person cameras, inspection, collision, repair, relay construction/dismantle, doors and return/reload | Broader interaction vocabulary and production tuning; individual mechanics retain their actual tested scope |
| Input mapping | ◐ | Working keyboard/mouse controls and action inputs | User remapping, controller support, device-specific accessibility and saved input profiles |
| Physics / colliders | ✅ current bounded shapes | Capsule traversal and static oriented-box collision, steps/slopes/walls, camera obstruction and occupancy checks | Imported collision authoring, more dynamic rigid bodies and full vehicle handling/cooling/reliability simulation; visual meshes do not automatically become colliders |
| Player state / state machines | ◐ | Grounded/falling/camera modes and chapter power/door/hazard/action states | Animation state machines, abilities, inventory/equipment/health balancing and broader progression |
| Saving / loading / recovery | ✅ current formats | Scoped IDs, chapter content fingerprints, journaled authoring/history, durable gameplay storage, interruption/retry and process restart proof | AIBD2 instances and exact project-owned dependencies survive restart; cloud player-save sync is not implemented by Drive development backups |
| Game objects / transforms | ✅ current box/mesh instance slice | Persistent identities, typed fields, position/size/rotation, world/chapter objects and dependency previews | Persistent imported-mesh instances and visual transforms are verified; wider prefab/component authoring follows |
| Enemy / NPC simulation AI | ☐ general behavior framework | Existing chapter NPC cues are authored rules | Enemy senses/behavior, navigation/pathfinding, faction encounters and boss behavior — M6 onward |
| AI-assisted creation | ✅ limited local-model workflow | One installed Qwen request verified through native Preview, explicit Apply and Save; structured selected-object field edits, rejection/cancellation safeguards | Broader tools, placement generation, lore retrieval and durable generation provenance; this is separate from NPC behavior AI |
| Network / multiplayer / anti-cheat | ☐ | No game-network stack is claimed by Studio's other network features | Session authority, synchronization, online services and anti-cheat only after gameplay/network requirements are defined; companion connectivity remains a separate staged feature |
| Tools engineering / production tracking | ✅ current tools slice | Custom SDK, creator hosts, native previews/isolated Play, mesh cooker/catalog, release verification, architectural ledger, milestone queue and organized Drive checkpoints | Wider creator workflows, project packaging and eventually more automation; no background Drive sync service implied |
| Structural / prop / modular assets | ◐ | Box-based world plus self-authored imported 4,788-triangle/eight-material cooling reference | Persistent visual placement verified; authored modular sockets, snapping, contextual prop interactions and a fuller hardware kit next |
| Character / creature art | ☐ production characters | BS has a temporary native proxy | Personal character designs, enemies/NPC meshes, textures, LODs and licensed/source-controlled final assets |
| Rigging | ☐ | No skeletal deformation system in the game renderer | Skeletons, skin weights, bone transforms and bounded skinning/import workflow |
| Keyframe / motion capture | ☐ | No skeletal animation pipeline claimed | Clip import, interpolation, transitions, root-motion rules and optional performance capture |
| Technical animation | ☐ | Existing movement/collision is not a ragdoll or animation blend tree | Animation state graphs, ragdolls, cloth and other secondary motion after the character pipeline |
| Materials / render pipeline | ◐ | Actual triangle rendering with normals, constant base color/emission and validated cooked material slots | UV/tangent/image import, texture sampling, PBR/lighting/shadows, reflections/post-processing and graphics controls in dependency order |
| Lighting / environment / VFX | ◐ | Existing fixed directional surface shading and emissive color | Authored lights/shadows, sky/environment lighting, lightmaps where useful, particles/fog/volumetrics — M5 and later rendering slices |
| Sound effects | ☐ game audio production | No implemented native game SFX pipeline claimed | Footsteps, machinery, coolant, power restoration, interaction and hazard cues |
| Voice acting / Adam audio | ☐ production voice | Adam's current native guidance is authored text | Choose a personal voice treatment, record/produce lines, timing/subtitles and contextual playback; no generated text is a recovered quotation |
| Music | ☐ | No game adaptive-score implementation claimed | Original/licensed music, stems, state transitions and pacing tied to regions and actual events |
| Audio implementation / mixer | ☐ | Studio audio tools do not establish a native game mixer | Playback/voices, mixing, attenuation, spatialization, occlusion/reverb and load budgets; Wwise/FMOD are candidates, not selected dependencies |
| HUD | ◐ | Native chapter status/action/hazard/Adam cues | Inventory/equipment/navigation feedback, readability/accessibility and production presentation |
| Diegetic UI | ☐ general system | Hardware-themed world/interface concepts | Real in-world panels and interactions, world-space rendering, input focus and accessibility |
| Game menus / settings | ◐ | Prototype native controls and creator navigation | Title/save-slot/options flows and supported display/graphics/input/audio settings; earlier setting lists are design targets rather than implemented controls |
| Feedback / game feel | ◐ | Interaction feedback, contextual hints and hazard/state changes | SFX, animations, carefully tuned camera/haptic effects and readable consequences; accessibility options before heavy screen effects |
| Economy / crafting / inventory | ☐ general economy | Mechanical relay construction and state checks exist | Resource accounting, item ownership/rarity, crafting recipes, vendor pricing and balancing — M6 onward |
| Rewards / achievements / unlocks | ◐ | Saved restoration/door/region outcomes and authored progress gates | Platform achievements, broader ability rewards and validated progression rules; no Steam achievement integration claimed |
| Region / level progression | ◐ | Current chapter regions, returns, persistence and bound content | Larger-map loading/streaming, level transitions, residency/LOD and broader campaign progression — M7 onward |
| Release / production management | ✅ current development record | Tested packages, retained prior releases/SDKs, source/evidence hashes, exact handoffs and checkpoint manifests | Production schedule, asset task ownership, content reviews, measured performance, recovery/clean-machine qualification and complete private-alpha acceptance |

## How the prototyping guidance applies

Keep playable graybox routes and the reference BS capsule available while detailed visuals grow. Validate door clearances, slopes, steps, jump/fall behavior, camera obstruction and interaction reach against the actual controller. Do not impose the pasted example doorway/jump dimensions or a 15-second modeling target as requirements for this existing game.

Detailed meshes are allowed during prototyping when they test an actual pipeline need. The current task is precisely to prove native imported parts can be authored and saved; it does not require finishing PBR, animation or audio first. Keep imported visuals separate from existing collision until an explicit collision-authoring contract is implemented.

Grid/checker textures, snapping and functional colors are useful planned authoring aids. A checker texture and sharp shadow path are not implemented merely by listing them. Current color/emission rendering can provide readable blockout distinctions without claiming texture/shadow support. Color should not be the only indicator of hazards or interactions.

The existing hook is established: BS explores and restores/builds the AI-BS hardware world, with meaningful repairs, construction, routes and saved outcomes, guided by Adam's memory. First- and third-person movement are already tested. We do not need to re-ask those original design questions to proceed.

## Next order

1. ✅ Persistent visual placement delivered: pinned references, exact project-owned dependencies, Preview/Apply/history/Save/restart, native viewport/Play and Studio97 desktop delivery. Preserve this foundation as content grows.
2. Extend the [environment asset plan](environment_asset_plan.md) through texture/material/lighting paths while preserving tested routes and personal chapter meaning.
3. Complete M5 audio/subtitles, supported PC settings, pacing and the state-driven RTX 4090 awakening.
4. Follow the existing milestone roadmap for combat/equipment/NPC behavior, larger-world streaming, vehicles and companion/network features rather than starting all pillars simultaneously.
