# Adam movement core

This is a CPU-only checkpoint 5 foundation, not a completed in-game companion.
`GuideController` owns a separate `GroundedCharacter` collision/query world.
There is no dynamic Adam body in BS's world and no reference to gameplay stores,
quests, authoring commands or repair/build operations.

## Authoritative inputs

- Supply a bounded authored graph (256 nodes, 512 edges). Edges can name a door
  or bypass gate; missing gates are closed. BFS order follows authored edge order.
- Supply actual grounded BS feet and the current collision snapshot revision.
  Grounded samples at least 25 cm apart form a runtime trail of at most 512
  points. Airborne samples, scene replacement, Recall and position discontinuities
  over 1.5 m break the trail. These samples must come from BS's controller.
- Apply door/build collision updates to the guide with `set_scene`. Both metadata
  gates and physical sphere/support queries must permit a step. A stale open gate
  cannot cross a physical wall, and stale graph segments cannot cross missing floor.

Follow uses a cached graph waypoint cursor, then the validated BS trail when no
graph path exists. It walks at 3 m/s and catches up at 5 m/s beyond 6 m, retaining
1.8 m personal space. It never jumps. Steps run at 60 Hz with at most four ticks
per call; discarded time is explicit. `suspend` clears partial time without
inventing progress. These are tunable prototype metrics, not a final game-feel pass.

## Persistence and recovery

Only `GuideIntentRecord` belongs in the future companion save schema: Follow or
Wait intent plus a validated waiting anchor. Runtime pose, physics ticks, trails,
waypoint cursors and eventual bone/animation state do not become history.
Restoring reconstructs a supported collision character at that anchor, then
resumes the saved intent. This module does not implement AIBD3 or store writes.

Explicit Recall checks at most sixteen supplied candidates. Each must lie 0.9–4 m
from BS and pass independent capsule clearance and stable nearby floor support.
Failed candidates preserve the complete old state. Accepted Recall retains the
Follow/Wait intent, updates its anchor, and discards stale movement caches.

`set_scene` preserves its old scene on rejection. **Its failure must never veto an
otherwise valid BS door/build action.** If a BS edit embeds Adam's old pose, the
adapter should retain the accepted gameplay edit, stop guide stepping because
its revision is stale, and report that Recall is available. The explicit
`recall(latest_scene, player, candidates)` overload can publish the latest
collision snapshot and a validated new guide pose atomically. There is no
automatic rematerialization.

## Verified scope

Standalone tests compiled with MSVC C++20 `/W4 /WX /permissive- /EHsc`, linking the
existing installed SDK `AIBS::Physics`, in both Release and Debug. No GPU/window
tests ran. Source CMake was intentionally not modified during this subtask.

Evidence is under `D:/AI-BS-Game-Resources/workshop/guide-controller-test`:

- `red-build.log`: missing guide header before implementation.
- `green-build.log`, `green-build-2.log`, `diagnostic.txt`: initial behavioral
  failures and diagnosis. Recomputing attachment every tick caused waypoint
  reversal and stopped a valid 12 m route outside the 3 m attachment radius.
  The route cursor and cache-first following fixed the root cause; door and
  movement assertions were retained.
- `recall-scene-red.log`: missing latest-scene Recall overload before addition.
- `final-release-test.log`, `final-debug-test.log`: passing full guide fixture.

The fixture exercises main-door closed/open, stale metadata against a physical
wall, alternate bypass, grounded trail following, revision invalidation, broken
trail across player teleport, supported Wait/restart, invalid saved anchors,
valid/invalid Recall, geometry replacement rollback, explicit recovery into the
latest scene, bounded time, fixed ticks across 60/120 Hz render cadence, and
missing-bridge support checks.

Source SDK0.11 now adds AIBD3 optional intent/anchor persistence, native F6/F7/F8 controls, authored gated route proof, contextual state hints and fresh-process restart. See COMPANION_RUNTIME.md and companion_integration_verification.json. Recall checks final settled personal space as well as the requested point. Dedicated indexed rendering and a temporary articulated in-place animated figure now pass native and installed SDK GPU proofs; see CHARACTER_RENDERER.md, GUIDE_PRESENTATION.md and indexed_character_integration_verification.json. Adam likeness, contextual gesture triggering and complete packaged opening acceptance remain unfinished.
