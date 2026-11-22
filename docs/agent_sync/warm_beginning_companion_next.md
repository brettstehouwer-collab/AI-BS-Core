# Next companion integration slice — proposed, not implemented

Reviewed after the authored-lighting integration. Existing GuideController CPU
contracts provide door-aware routes, grounded BS breadcrumbs, independent
collision queries and explicit latest-scene Recall. Native movement, durable
intent, character rendering and the likeness remain unfinished.

1. Preserve the no-argument legacy `first_boot_content_schemas()` registry.
   Add content-aware selection only when AIBD3 declares a companion. Lighting-only
   AIBD3 and all old saves must retain their existing registry identity.
2. Seed one optional companion intent record from the immutable binding. Keep
   the six chapter records unchanged. Persist Follow/Wait and a waiting anchor,
   never footsteps, breadcrumbs, bones or animation frames.
3. Extend chapter View deliberately: allow only the declared companion UUID and
   exact schema. Ordinary BS actions must preserve companion state; companion
   actions must preserve hardware, door, quest and progression records.
4. Existing batches require semantic events. Proposed decision: append an
   honest bounded CompanionOutcome family for Follow/Wait/Recall, preserving all
   existing variant indices and wire encodings. Do not mislabel Recall as a
   repair, quest or invented boolean mechanism change. Verify codec, admission,
   recovery and legacy bytes before native integration.
5. ChapterLive owns Adam separately from BS. Stage durable commands and candidate
   guide state before publication; rejected admission leaves pose and intent
   unchanged. A door/build edit that invalidates Adam must still succeed.
6. On restart, an anchor invalidated by a later BS edit preserves the world and
   enters blocked/Recall-required state. Never silently teleport, reseed, veto
   BS or reject the entire save. Validate new Wait/Recall anchors for support,
   clearance and personal space before accepting them.
7. F6/F7/F8 are available for explicit Follow/Wait/Recall, subject to native
   input, pause and inspection gates. Add concise contextual feedback.
8. Introduce owned indexed character resources and per-frame transforms for an
   articulated placeholder, then the approved skeleton path. Do not use the
   4096-vertex transient stream or rebuild static scenery each frame. Adam has
   no collider that obstructs BS and never performs repairs for the player.

Verification order: legacy registry/codec compatibility; command rollback and
exact state isolation; SQLite restart; native controls; dedicated GPU figure;
both routes with closed doors, build/dismantle, Follow/Wait/Recall, departure,
fall recovery, pause and restart. No external blocker was found by the review.

This records proposed engineering choices within the approved phase. It is not
evidence of a completed companion, character asset, animation or opening.
