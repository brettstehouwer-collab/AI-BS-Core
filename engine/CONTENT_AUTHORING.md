# Typed chapter authoring and structured AI proposals

`ContentAuthoringHost` owns an authored chapter document. It is the shared SDK
admission path for typed property edits, fixtures and hardware, independent of
runtime player state. The source AI-BS Chapter creator now connects through its
own managed native endpoint. Managed isolated chapter Play and its native 3D viewport are connected. Generic numeric editing and its DX12 preview remain intact.

## Current owner contract

An edit request carries an operation ID, expected authoring head, exact content
fingerprint, label and grouped edits. Supported edits set authorable fields,
create/erase fixtures and create/erase hardware. Targets use persistent UUIDs.
Observation rows describe authorable properties; they are not gameplay component
records. Door state, repair outcomes, discoveries and quest completion cannot be
set through this interface. Authored defaults retain their existing validation.

One group stages all changes, then validates the final chapter through
FirstBootContent. Intermediate layout states are private; a create-and-position
gesture can validate as one operation. Preview returns a private immutable
candidate and actual dependency/new-Play-branch assessment. Apply checks its
owner and generation. Publication, history and Save invalidate prepared handles.
Original requests are copied and retained for exact retries; an operation ID
with different bytes rejects. A retry after Undo does not resurrect the change.

Undo/Redo restores exact content snapshots while the authoring head advances.
Content revision high-water never decreases, so a new edit after Undo cannot
reuse an already issued content revision. Known/deleted UUIDs remain reserved.
Optional reserved IDs carry lineage into an explicitly created branch. The host
rejects UUID recycling, foreign scope/head/fingerprint and runtime-only writes.

The AIBA version1 authoring document stores a canonical baseline, reserved IDs,
accepted edit/history requests, current head/fingerprint and checkpoint ID. Open
checks its CRC32, bounds and canonical replay. Content uses its existing SHA-256;
CRC32 is corruption detection, not file authenticity. Receipts, Undo/Redo and
retired identities survive reopening. No gameplay outcome is fabricated by the
authoring journal, and existing player databases are not selected or rewritten.

Save uses an explicit slot under an existing directory, an exclusive sidecar lock,
same-directory staging, flush and Windows atomic replacement. A new owner refuses
to overwrite an existing slot; reopen it explicitly. Reopened owners compare the
previous full bytes before replacing a document, rejecting stale cooperating
writers. Save As requires an explicit new document/branch. This is not a universal
power-loss guarantee or protection against uncooperative privileged filesystem
changes. Visible Apply and successful Save remain separate states.

Admission bounds:256 edits/request,256 accepted edit/history operations per journal,
1MiB request/document,10,000 known identities,16MiB conservative logical history
charge,8 active prepared candidates and16MiB aggregate prepared charge. These do
not bound caller-retained stale snapshots or total RSS. No history is silently
evicted. Explicit branch/compaction work is required once a document reaches its
budget. Journal replay performs real validation and is not a frame-loop operation.

## AI authoring integration: actual scope

`native_studio.game_engine.content_proposals` is a strict structured-output
adaptor. It does **not call a model**, execute code or launch tools. A controller
pins document identity/head/fingerprint, an allowed target/field/type set and a
stable operation ID. Model output supplies only a version, label and field edits.
Duplicate JSON keys, unknown properties/targets, runtime fields outside the
capability set, wrong types and nonfinite values reject. Strings are bounded and
encoded as data. This first adaptor supports field proposals; creation operations
already exist in the SDK and need their own model-tool exposure.

The adaptor emits an AIBP version1 scoped packet containing project, branch,
world/definition UUIDs and the typed request. The receiver uses
decode_scoped_content_edit and the scoped ContentAuthoringHost entry point; it
does not replace the proposal's scope with the currently open document. A real C++ document fixture verifies
publication, exact retry, wrong-branch/stale-output rejection and physically invalid doorway
rejection without changing saved bytes. The C++ owner independently enforces the
domain rules, including when a caller supplies a bad capability set.

This proves structured-proposal admission, not live AI generation or a finished
chat-to-world interface. The managed endpoint and typed visual controls now use
this same owner. A controller-owned job context reaches a visible native Preview
and waits for Apply. A local provider now connects through this job path; see AI_AUTHORING.md.
Adam's personal in-game guidance/source memories remain distinct from the AI that
helps author levels or code. Human authorship, source evidence and model labels
must not be conflated; the proposal label is metadata, not verified provenance.

Relevant implementation and proof:

- `include/aibs/content_authoring.hpp`, `games/content_authoring.cpp`
- `tests/content_authoring_tests.cpp`
- `tests/test_content_proposals.py`
- `examples/sdk_consumer/main.cpp`
- `out/authoring-final.Debug.log`, `out/authoring-final.Release.log`

No new frozen Studio/public-site deployment or new model dependency is introduced.
The original M4 source gates are now verified. Broader AI tools/providers and the
complete personal First Boot alpha remain unfinished.

## Managed endpoint, visual tools and proposal jobs

The new `aibs_content_host` advertises `chapter-authoring-v1` using the existing
creator framing. It opens only the explicitly selected chapter directory and
`chapter.aiba` document; it does not open numeric `world.aibs` or player saves.
Describe and bounded UUID-sorted pages expose authorable typed rows. Scope,
expected head, fingerprint, host epoch and prepared-token checks remain native.
The client retains original wrapped bytes for retries; reopening or closing a
process never silently replays or saves an uncertain edit.

In source AI-BS, open Engineering & Specialized Labs Ã¢â€ â€™ AI-BS Game Engine Build Ã¢â€ â€™
Chapter creator. New project selects an existing folder and writes separate
`.aibs-chapter-project.json` metadata. The UUID outliner and typed inspector offer
Preview/Apply, fixture creation/removal, Undo/Redo and explicit Save. Dependency
previews distinguish saving the authoring journal from compatibility with old
gameplay branches. The source UI is not included in the retained Studio94 binary.

`ContentProposalJobs.begin` captures actual owner generation, full session scope,
definition identity, head, fingerprint and permitted typed fields. A returned
JSON-friendly prompt is a copy; changing it cannot change the pinned context.
`ContentView.submit_proposal` consumes a matching structured reply and asks the
native owner to prepare it; the visible document changes only after Apply.
Edited, replaced or closed contexts reject stale replies, and close cancels jobs.
Job management runs on the owning UI thread. Bounds are eight jobs,256KiB per
prompt and1MiB in aggregate. Only field changes are exposed in this first job
contract; integer tools and generated object creation still need explicit APIs.

No model is invoked by these components. Text from a provider must return through
this job path rather than write project files directly. Adam's authored memoir
guidance is separate from model output. Managed chapter Play/Stop and native chapter preview now use immutable exported
definitions through parent-owned processes; see CHAPTER_PLAY.md.

Current process/UI proof is recorded in `out/chapter_creator_verification.json`;
the older owner-only proof above remains historical evidence.


Revision0.20: native chapter preview/Play, pending-save Stop, rapid publication
and source/installed proofs are recorded in `out/chapter_play_verification.json`.
The earlier revision0.20 tests did not call a model. Revision0.21 adds actual
selected-model inference; see AI_AUTHORING.md and ai_authoring_verification.json.


Revision0.21 connects local model discovery, capability preflight and actual
structured inference to ContentProposalJobs and the same native Preview. Only
explicit Apply/Save changes or persists authoring. Provider metadata remains
session metadata; generated prose is not automatically verified memoir evidence.
