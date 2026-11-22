# M1 native motherboard obstacle course — SDK 0.6

The course is an independent game module and project above the generic AI-BS engine. It proves grounded movement on authored, saved motherboard geometry while preserving the existing First Boot prototype and original numeric schema/checkpoints.

## Play and author

Launch `aibs_motherboard.exe --obstacle-course` or the course button in the native build workspace. Its default slot is `%LOCALAPPDATA%/AI-BS/MovementCourse/native-course.aibs`; the project is movement-course/main. The ordinary no-argument player continues to load the original FirstBoot world. `--checkpoint PATH` explicitly chooses a different slot for the course.

WASD/arrows walk, right-drag looks, Space jumps, Shift sprints, V switches views, F2 enters explicit inspection flight, E/left-click repairs the course relay, F5 retries saving and F9 reloads/returns. Falling below the yard returns BS to its entrance. This is a development traversal yard with authored guidance and a temporary BS proxy, not Jenison, the sheltered hub or a completed story chapter.

The course includes socket stairs, a cyan 20° CPU access ramp with upper platform, a red 60° barrier, a GPU service wall, DDR5 towers, an RTX landmark and a repairable relay. Dimensions are authored game geometry, not a measured motherboard CAD model. Its separate SDK schema persists transforms, quaternion rotation, kind and repair state. Quaternion edits change actual render vertices, normals, picking and collision. The source test changes a ramp to 30° through ordinary authoring transactions and preserves it across checkpoint reload.

## Completion evidence

`native_obstacle_course` runs two real native processes through `verify_obstacle_course.py`:

1. Traverse the socket steps; ascend beyond the ramp onto the upper platform while retaining support; descend to the lower floor; reject forced 60° ascent; collide with the wall; fall from the board and recover.
2. Exercise Win32 focus loss, held-key clearing, queued-jump cancellation and minimize/restore. Movement must not append authoring or Adam records.
3. Position the actual player camera at the relay, send a Win32 E press, and use the same camera-ray interaction handler as interactive play. Save the repair once.
4. Start a second process, load the same checkpoint and verify world/entity IDs, checkpoint head, source orientation, repair state and history. The overview GPU capture must match exactly. The slope-specific GPU capture must also be nonblank.

The report is `engine/out/obstacle_course_verification.json`. A passed report requires strict true booleans for steps, slopes, walls, falls, focus, restart and interaction, plus zero GPU validation errors when recorded. Missing, false or malformed evidence cannot show success in the build monitor. The default renderer/GPU, saved-world edits/undo/redo/dismantling and checkpoint interruption/budget tests still run separately.

Physics fixtures additionally verify supported 20° and 30° ascent/descent/transitions, gravity sliding on a 60° surface and a blocked oversized step. Scene fixtures compare rotated mesh normals/surfaces to oriented picking, reject nonunit/nonfinite rotations and transformed overflow. Player fixtures verify camera volume edge clearance, tight-ceiling first-person fallback, short boom/body clipping visibility, first/third-person controls and focus cancellation. Fixed ticks are compared across render cadences.

The camera is now a swept sphere with clearance; zero radius uses a ray. An occupied anchor rejects the sweep; the player uses a valid eye point when a tight space fits the capsule but not the camera sphere. The avatar proxy is hidden when the resulting camera would be inside/too close to its configured body.

## Compatibility and remaining work

SceneObject adds an identity-default quaternion, preserving existing source aggregates but requiring SDK clients to rebuild for0.6. All old FirstBoot source schemas remain unchanged; existing format-1 checkpoints are not silently migrated. The synthetic course uses its own scoped save and source schema.

M1 is complete only with matching consolidated Debug/Release and installed-consumer evidence recorded in BUILD_STATUS. This proof does not implement a full character animation system, dynamic rigid bodies, terrain, interpolation, saved player/respawn components, vehicles, navigation, networking or the private FirstBoot alpha. M2 now supplies the typed admission foundation; actual SQLite worker/recovery/import remains the next build.
