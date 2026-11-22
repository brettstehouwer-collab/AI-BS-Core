# Grounded BS movement — SDK 0.6

This is the first M1 runtime slice in the [continuing roadmap](BUILD_ROADMAP.md). It adds grounded traversal to the existing persistent motherboard world. M1 now has a verified native obstacle course with true slopes and real-process restart. See MOVEMENT_COURSE.md and the consolidated evidence in BUILD_STATUS.

## Dependency and SDK boundary

`AIBS::Physics` hides Jolt behind AI-BS value types and a move-only `GroundedCharacter`. `AIBS::Player` provides the transient player/camera controller. Both are exported with `AIBS::Engine`; the First Boot game module chooses its own spawn policy. Existing installed clients must rebuild against `find_package(AIBS 0.6 CONFIG REQUIRED)`.

Jolt 5.6.0 is pinned to commit `e77f175595e64cb44218cc9d9d56fc365ad0e36a`, with SHA-256 archive checking. See [dependency lock](cmake/JoltDependency.lock.json), [build profile](cmake/JoltDependency.cmake) and [MIT license](third_party/Jolt-LICENSE.txt). First configure requires network or a provisioned FetchContent source cache. The static library uses the x64 SSE2 baseline, with optional AVX-family instructions disabled. Its headers, library, CMake dependency configuration and license are installed alongside AI-BS. No separate Jolt runtime DLL is required.

## Implemented behavior

- Capsule defaults: 1.8 m high, 0.35 m radius; walking 7 m/s, sprinting 12 m/s, gravity 18 m/s², jump speed 6 m/s, step height 0.4 m. These are prototype gameplay values, not settled balance.
- Physics advances at 60 Hz independently of render calls. Each advance performs at most eight ticks and accounts for dropped elapsed time. This does not promise cross-platform bitwise determinism.
- Current immutable oriented scene boxes become matching rotated static colliders whether selectable or not. A bounded replacement is staged before publication; an occupied-capsule overlap rejects the replacement without changing collision geometry, player state or authoring history.
- The native game previews authoring changes and stages matching collision/render geometry before publishing its candidate world. It then attempts the existing synchronous checkpoint. Failed storage remains visibly UNSAVED; the SQLite worker is M2 work.
- WASD/arrows walk; Space jumps on press; Shift sprints; right-drag looks; V switches cameras. F2 explicitly enters developer inspection flight, which moves the camera and freezes BS. Space/Ctrl move vertically only in that mode.
- Losing focus or minimizing clears input, fractional time backlog and queued jumps, and pauses movement. Resume does not replay the suspension interval.
- First-person uses the capsule eye point. Third-person follows a five-meter boom with swept-sphere obstruction and clearance, falling back to a valid eye point in tight spaces. A temporary box represents BS; animation and a finished character model are future work.
- Temporary geometry uses two reusable per-frame upload buffers, capped at 4,096 triangle vertices, written only after the appropriate frame fence. It does not rebuild the static world or force a full GPU idle each movement frame.
- Walking, jumping and looking do not append authoring/Adam journal events. Player pose is transient. Startup, reload and falling select a clear point on the actual board, preferring the prototype entrance and then trying a bounded 9×9 grid. Existing buildings and UUIDs remain intact. This may miss a narrow untested opening; an obstructed grid gives a recovery error.

## Verification and evidence

`physics_contracts` covers gravity, floor/wall collision, sliding, short steps, jumping, fall/reset, render-rate independent tick accounting, bounded catch-up, nonselectable solids, live overlap rejection/rollback, camera-ray obstruction and suspension of queued input. `player_movement` covers the control/camera/focus integration. First Boot tests cover saved construction blocking the entrance, fallback after load, shifted-board spawn, and explicit failure when all candidates are blocked.

`native_grounded_movement` executes real Win32 controls and native DX12 rendering on the selected adapter. It checks live construction rejection, focus clearing, changed pixels for the BS proxy, repeated transient-buffer reuse, removal, malformed/oversized rejection and unchanged world history. Its actual result is [movement_verification.json](out/movement_verification.json), with a GPU capture at [movement-render.bmp](out/movement-render.bmp). The ordinary scene/save/restart tests continue independently. Consult [BUILD_STATUS.md](BUILD_STATUS.md) for consolidated Debug/Release and installed consumer results.

## Remaining limits and next steps

Collision geometry is currently oriented static boxes. True 20°/30° ascent/descent and platform transitions, steep60° rejection/sliding and oversized-step blocking are verified. Camera obstruction uses a swept sphere; a blocked anchor triggers a valid-eye fallback. Proxy visibility accounts for short booms and the configured body bounds. There are no moving/rotating bodies, vehicles, fluids, terrain collision, network prediction, animation, navigation or saved player/respawn components. Render updates are not yet interpolated between physics ticks.

M1 proof is the independent two-process motherboard course, alongside generic scene/physics/player and existing saved-world tests. Next is M2's bounded transactional SQLite worker and identity/history-preserving format1 import. Its typed semantic/component admission foundation exists, but it is not yet the game's save implementation. The public browser playground remains separate; new story content stays in the private PC alpha path.
