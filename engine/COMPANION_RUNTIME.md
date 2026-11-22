# Native companion intent and movement

`AIBS::CompanionRuntime` integrates the independent GuideController with an
explicitly declared AIBD3 companion. Legacy chapters, lighting-only AIBD3 and the
no-argument content registry keep their existing schemas. A companion chapter
selects one additional `firstboot.CompanionIntent` v1 record using the binding
UUID: Follow/Wait plus a canonical float waiting anchor. The six authored
chapter defaults remain unchanged. Existing bound saves are never implicitly
migrated to another registry or content fingerprint.

Follow, Wait and Recall have an appended `CompanionOutcome` event, payload and
canonical envelope version3. All six older variant indices and their v1/v2 wire
encodings remain unchanged. Explicit choices have one intent delta and one
honest event; runtime footsteps, breadcrumbs, bones and animation frames never
enter permanent history. Repeated Follow/Wait selections invent no events.

## Publication and recovery

1. `prepare_choice` checks the exact world head and authoritative grounded BS
   evidence, constructs a separate supported guide candidate and returns an
   immutable request. Live pose, saved intent and the world stay unchanged.
2. Pass that request through `GameplayWorld::prepare`, with `validate_choice` as
   the domain validator. It checks the staged request bytes, current BS evidence,
   head and every unrelated component. Companion choices cannot repair hardware,
   open doors, change NPC quests or grant route/shelter progression.
3. Admit through `GameplayWorld::publish`. On rejection, discard the candidate;
   Adam and both world heads remain unchanged. On acceptance, call the runtime's
   allocation-free `publish` immediately, with no intervening frame/sync call.
4. Actual asynchronous completion advances the durable head. An already accepted
   choice whose later COMMIT fails remains visibly UNSAVED for retry, following
   the existing world contract. Acceptance is never reported as durable saving.

Prepared choices belong to one owner and runtime epoch. Movement, suspend,
synchronization or another accepted choice invalidates an old candidate.

After accepted BS construction or door changes, `synchronize` adopts the new
collision scene. An invalid guide pose suspends Adam and requires explicit
Recall; it cannot veto or roll back BS's edit. On restart, a structurally valid
anchor that is now embedded/unsupported preserves the save and enters the same
Recall-required state. Original authored spawns still undergo physical content
validation when the chapter is created.

Recall checks support, clearance and distance both before and after settling the
candidate. The final feet must stay within personal-space bounds. This includes
a regression where an elevated requested point passed the original distance
test but settled too close to BS. Failed Recall changes nothing.

## Native integration and presentation boundary

F6 Follow, F7 Wait and F8 Recall are edge-triggered native controls. Paused,
inactive and inspection input cannot publish them. F9 reconstructs movement from
saved intent/anchor. The owner supplies actual BS feet/grounded state and current
door UUID/role states. The runtime combines authored gated routes with grounded
BS trails, uses its own collision/query world, and adds no collider to BS's
scene. Runtime walk/catch-up speeds derive from current BS defaults so he can
keep pace; the standalone controller's original defaults remain unchanged.

Companion choices update semantic scene revision without replacing static GPU
scenery. Movement also performs no static-scene replacement. The native report
exposes an optional valid guide pose. The dedicated indexed renderer now draws
a temporary articulated figure; native reports set `character_rendered:true` only
when paired GPU readbacks prove actual figure pixels. Adam likeness remains
unfinished. See CHARACTER_RENDERER.md and GUIDE_PRESENTATION.md. A
Recall-required state has no renderable pose; do not draw the default blocked
return value from `advance` as a character at the world origin.

`native_companion` drives actual native key messages, holds a real save credit
to prove rejected publication, tests inspection/inactive gating, F9 and separate
process restart, then walks both existing progression routes with Adam. CPU
contracts cover exact isolation, invalidated anchors, stale choices, unsupported
Recall, SQLite recovery and failed admission. These checks do not constitute a
finished visible/animated Adam, likeness, audio playback or packaged opening.
