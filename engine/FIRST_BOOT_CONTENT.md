# Authored First Boot content and runtime continuity

`aibs/first_boot_content.hpp` adds the game-owned content foundation planned for
M4. It is an SDK/runtime API. Typed CreatorHost commands, visual chapter editing
and the managed native Play/Stop window are still required. Existing numeric
projects and the native authoring preview remain available; they do not silently
turn into chapter documents.

## Definition, defaults and saved outcomes

`FirstBootContentDefinition` describes an authored chapter: stable definition,
world and binding UUIDs, uint64 content revision, hardware, three door roles,
fault/switch/socket geometry, hub/Pencil region volumes, NPC/lamp anchors,
fixtures, ordered return candidates and optional authored Adam cues.

The six initial chapter records contain validated new-game defaults. Editing
them cannot grant shelter, repair a fault, complete a quest, fabricate a route or
invent a recovery. Runtime state owns those actual outcomes and semantic receipts.
Hardware capacities may be authored starting conditions; they are not retrospective
player actions. Personal memoir evidence is not encoded as a generated gameplay
outcome. Current NPC provenance remains fictional/authored; verified memoir
attribution requires a separate source adapter.

`FirstBootContent::create` validates and freezes a definition, normalizes collection
order, retains its canonical bytes and computes SHA-256 through Windows CNG.
`from_template` derives a definition from the existing native First Boot factory
and protected chapter geometry, rather than inventing a Python replica.
The API exposes the definition through a const reference. This is an immutable
trusted-C++ API, not an untrusted-code sandbox or a complete typed authoring journal.

`first_boot_content_baseline` creates a new authored runtime baseline with a
`firstboot.ContentBinding` record. That record binds the definition UUID, canonical
revision string and exact SHA-256. It cannot be changed by gameplay. Native scene,
region, player, rules, actions and hints receive the immutable content explicitly.
Runtime cannot move/rename authored hardware or geometry; new relays and genuine
repair/quest outcomes still use the established semantic batches.

The original `first_boot_chapter_*` APIs retain the fixed-template interpretation.
They reject content-bound saves. Existing `durable_first_boot_*` overloads still
require player-world context. New explicit overloads admit only the expected
player-world or temporary-Play context; the content adapter separately validates
its binding. Authoring and published-lore contexts reject. Actual scope/receipt
bytes are retained, without pretending a temporary Play world is the player save.

## Geometry and dependency checks

Content-aware scene projection uses the same hardware, door transforms, capsule
physics and runtime rules as the retained chapter. Layout coordinates come from
the definition; player outcomes remain in the runtime records. The hazard warning
uses the authored fault extents. Authored Adam cues replace named guidance states;
the normal contextual fault/recovery logic and committed outcomes remain separate.

Validation checks both grounded return states, each door's region relationship,
and actual bidirectional capsule traversal through all three open apertures.
Fault/switch/socket and NPC/lamp anchors need a supported local approach in their
declared regions. These are bounded physical probes, not global pathfinding,
navmesh generation or a proof of every possible construction arrangement.
Runtime construction/door changes revalidate their resulting scene and return.
The primary shelter return agrees with the authored spawn witness.

`first_boot_content_preview` freezes and validates a proposed revision, reports
affected UUIDs and render/collision/power/quest dirty flags, and returns a private
candidate. Dialogue-only changes do not request geometric rebuilds. Rejected
proposals return no candidate. An existing UUID cannot silently change category.
The typed host must additionally own retained authoring identities/history; the
definition snapshot alone is not an undo/tombstone journal.

Save compatibility here means exact definition binding, not guaranteed storage
publication. An unchanged fingerprint remains compatible with saves already bound
to it, subject to normal store/domain validation. Changed content requires a newer
retained revision and a **new Play branch**. No automatic in-place migration is
implemented. Legacy player saves are retained in their original interpretation;
they are not silently imported into the new content baseline.

## Codec, limits and evidence

The separate AIBD version1 codec admits at most1MiB,512 hardware entities,512
fixtures, six chapter defaults,128 return candidates per region and32 cue entries.
Text/numeric/component encoding reuses bounded strict codecs. Decode rejects
unsupported/trailing/truncated or noncanonical data and revalidates physical
dependencies. The original `.aibs` format, semantic codecs and SQLite layouts are
unchanged. ContentBinding is an explicit additive registry type for new contexts.

The native fixture exercises moved door/socket/NPC geometry, authored cues,
isolation, relay build/connect/disconnect/dismantle, optional decline, downstream
repair, actual capsule crossing and SQLite restart. It also rejects fabricated
progress, wrong bindings/contexts, blocked routes and UUID category reuse, and
checks dialogue-only dependency flags. A proof helper independently compares the
encoded definition SHA-256 against Python hashlib. Relevant files:

- `tests/first_boot_content_tests.cpp`
- `out/verify_first_boot_content.py`
- `out/first_boot_content_verification.json`
- `out/content-final.Debug.log`, `out/content-final.Release.log`
- `examples/sdk_consumer/main.cpp`

The installed Studio release and public site are unchanged by this source/SDK
slice. The full M4 creator and personal20–30minute alpha remain unfinished.
