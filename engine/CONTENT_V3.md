# AIBD3 authored content

AIBD3 adds an explicit asset profile, controlled exposure and authored bindings
for a companion, lights and optional memory audio. Runtime lighting is now
projected from these declarations and authoritative supply state. Optional
durable companion intent and native commands are described below and in
COMPANION_RUNTIME.md; media playback remains subsequent integration work.
The existing six chapter initial records and registry identity remain unchanged.

The wire retains the complete AIBD2 field order, including placements, then adds:

1. One-byte `AssetContentProfile` and canonical float-representable exposure.
2. At most one companion: UUID, name, spawn, initial Follow/Wait flag, optional
   model reference, authored route nodes and edges.
3. At most 32 lights: UUID, name, directional/point kind, reserve/restored power
   binding, position, unit direction, normalized color, intensity and radius.
4. At most eight optional memories: UUID, name, interaction position and an
   immutable audio pack reference.

References are UUID/payload-SHA/pack-SHA triples. All content entity identities
are unique across old and new families. Route node/edge order remains authored
because it determines deterministic equal-path selection; binding collections
serialize in UUID order. Unknown flags/enums, excessive counts, invalid routes,
nonfinite parameters, duplicate identities and trailing bytes reject. AIBD1/2
readers/writers retain their existing byte layout. New fields cannot be hidden in
an old version, and changed content previews cannot downgrade the format.

`warm_beginning` is selected explicitly when creating a new compatible chapter
branch. It requires AIBD3; existing chapters keep the legacy profile. Authoring
rows expose the modern profile read-only and exposure as a bounded number.
Placement create, typed edits, Undo/Redo and journal Save/reopen retain all
unrelated companion/light/media declarations. Preview continues to identify
changed content as requiring a new Play branch; existing bound saves are not
silently rewritten.

Modern placement publication verifies typed stored assets with a deduplicated
128MiB encoded closure and a separate 128MiB residency charge for decoded assets
plus expanded instance vertices. Surface composition applies the shared exact
image deduplication and global 32-image/256-draw/one-million-vertex bounds.
The base chapter and all placed vertices share the overall vertex limit.
Legacy publication retains its prior 64MiB accounting and v1 mesh loader.
Dependency validation runs before Preview/Apply/history/Save publication.

Temporary companions need no model dependency. Character and audio pack loaders
are not yet implemented: structurally valid model/audio references can be
round-tripped by the pure content codec, but authoring publication rejects them
explicitly. They are never silently omitted from a supposedly complete save.
Native companion commands/controls, audio controls and new typed dependency
families remain subsequent integration work.

## Optional companion runtime registry

`first_boot_content_schemas()` keeps the exact legacy registry. Its content-aware
overload selects one additional `firstboot.CompanionIntent` v1 schema only when
AIBD3 declares a companion; lighting-only AIBD3 retains the old registry. The
runtime baseline adds one record using the immutable companion UUID, separate
from the six authored chapter records. Its only fields are `follow` (boolean)
and `anchor_x`, `anchor_y`, `anchor_z` (finite canonical-float numbers within
plus/minus one million). Footsteps, bones, animation frames and trails are not
durable component fields.

`first_boot_content_companion_intent` reads this optional state;
`first_boot_content_companion_component` constructs its exact record shape.
Both validate structural values rather than rematerializing a guide. Full
chapter validation rejects missing, duplicate, foreign or malformed companion
records. Chapter actions and node construction preserve intent exactly.

A saved anchor can become physically invalid after BS builds or closes a door.
That does not invalidate the save or veto BS's edit. Recovery preserves the
intent and original anchor; the native owner must enter blocked/Recall-required
state and validate a new point only for an explicit Wait/Recall command. No
automatic relocation or save-registry migration is performed. Existing bound
saves require their exact known registry; choose a new compatible Play branch
when introducing a companion to old content.

`AIBS::ContentLighting` exports `first_boot_content_lighting`. It shares the
chapter's actual main/bypass supply predicates through
`first_boot_content_supply`, enables reserve lights before power restoration,
and enables restored lights only while a valid supply exists. It never changes
components, event history or shelter objectives. Chapters without authored
lights keep legacy rendering. At most one directional binding is allowed;
point bindings share the 32-light content bound. Creator and native Play publish
geometry, textures and this lighting projection together after accepted edits
or gameplay changes, without recomputing them each frame. See LIGHTING.md.
