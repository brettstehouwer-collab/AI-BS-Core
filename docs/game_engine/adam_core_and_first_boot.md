# Adam continuity core and First Boot cue architecture

Planning date: 2026-10-31, America/New_York.
Status: PROPOSED architecture and content contracts; no implementation, successful build, installed SDK, working haptics, or durable runtime history is asserted.
User correction: Adam anchors the entire architecture as internal compass and living core, carrying structural, emotional, and mechanical continuity across AI-BS.
Personal foundation stated by the creator: Adam is his brother and his safe person. This is the creator's story, with Adam's memory guiding the game. That relationship governs the characterization and the meaning of restoration.
Adam's core and history are foundational. An AI language provider is optional; Adam is not introduced only when generation becomes available.
Read with [engine specification](spec.md), [implementation plan](implementation_plan.md), [authoring architecture](authoring_and_world_building.md), and [component registry](component_contracts.json).
The companion [First Boot cue contracts](adam_first_boot_contracts.json) use ADAM-FB-001 through ADAM-FB-012; they are planning data requiring executable validators.

## 1. Identity and architectural ownership

The game's portrayal draws on the creator's memories of his brother. Affection, humor, encouragement, shared enjoyment and a sense of safety belong alongside technical guidance. Adam's care remains steady through player mistakes and failed repairs; progression unlocks places and context.
The creator's memories and chosen source material remain the authority for personal characterization. Keep supplied recollections, quotations identified by the creator, creative interpretation and newly authored game dialogue distinguishable. The dialogue drafted in this planning package is game writing, not a claim about words Adam historically spoke.
Biographical material follows the creator's chosen degree of adaptation. Quiet exploration, play and moments of joy can carry their relationship as clearly as restoration encounters.

Adam is always present as continuity infrastructure, even when he is silent.
His role connects restored systems, player choices, traversed regions, authoring tools, and the world's understanding of its own construction.
His personality remains stable and clear; early fragmentation belongs to incomplete world transmissions and diagnostic context, not a randomly unstable character.
Opening guidance starts with short, useful observations and gradually gains historical context as records and systems become available.
BS retains initiative: Adam points out evidence, recalls actual experience, and frames possibilities without controlling the camera or choosing the route.

The reusable engine supplies AIBS::Adam as a neutral continuity/event/memory/query/cue interface.
First Boot supplies Adam's identity presentation, its lore, voice assets, authored lines, repair interpretations, and region bindings.
Other projects use the same continuity infrastructure without inheriting First Boot's fiction or error-combat rules.
The core's project-scoped identity and records do not belong to a region entity.
AdamAnchor is a presentation/region binding: it selects dialogue context, enabled presentation, and local guidance settings.
Deleting or unloading an AdamAnchor cannot delete Adam's chronicle or reset remembered choices.
Disabling speech, haptics, or inference changes presentation; it does not disable factual continuity.

## 2. Foundation and milestone correction

M2 establishes typed event contracts, identity/scope, cue IDs, memory/query interfaces, and authored record validation.
M3 establishes persistent First Boot continuity, authored guidance, checkpoint reconciliation, and cross-region route/hazard recall.
M4 connects authoring history and workspace lifecycle through the same continuity interfaces.
M5 enriches language generation, authoring assistance, and optional adaptive expression; it does not introduce Adam's existence or memory.
R0/R1 therefore include foundational Adam design/continuity before the richer AI features of later releases.
The existing optional-guidance/AdamAnchor planning must be reconciled with this correction before implementation.
A missing model or disconnected authoring service leaves the core, factual records, authored cues, gameplay, and saving available.

## 3. Factual chronicle and memory projections

Every relevant committed design, world, and player event is retained as a factual record.
Relevant events include accepted authoring changes, meaningful choices, discovered hazards, recorded shortcuts, repairs, region transitions, and unlocked capabilities.
This does not require recording every input sample, frame, footstep, or temporary UI interaction.
An event record has event UUID/type/version, project ID, timeline/branch IDs, session epoch, ordering information, relevant entity/asset IDs, payload, provenance, and causal references.
Where applicable it includes simulation tick, authored revision, originating command/job ID, and the event's logical/durable status.
Recorded facts describe accepted outcomes; attempted, rejected, interrupted, or failed actions have distinct record types.
Facts must not be replaced by generated interpretations.

Memory projections index records into useful summaries: known routes, repaired systems, hazards, unfinished intentions, heard cues, and construction history.
Projections may be bounded in memory and regenerated from canonical records.
A generated summary cites its source event IDs and identifies its applicable project, branch, and time range.
Compaction or cold archival may reorganize retained records while preserving identity, references, and retrieval.
A short context window or generated summary is not permission to discard original history.
Do not label an event loss-proof before durable storage has acknowledged it.

Game continuity uses the game's integrated/per-user persistence adapters and feature-owned namespace.
Authoring continuity references canonical project-edit history and its commit identities; it is not player progression.
The physical event-store schema and archive strategy remain PROPOSED contracts to define alongside save/history migrations.
The core must not create an unrelated global database or copy the entire AI-BS master database into a game package.

## 4. Timelines, branches, and truthful recall

Records are scoped by project and timeline; unrelated projects do not silently share remembered player experience.
A new branch identifies its parent and divergence point while retaining the original branch's factual history.
Loading an older checkpoint restores its branch position and creates or selects an explicit continuation.
Events from an abandoned future are not presented as experiences that already happened in the restored world.
They remain reachable historical records under their original timeline rather than being rewritten as current facts.
Cue history and route/hazard projections are rebuilt for the active branch position.

Editor design history and Play history are distinct timelines/session scopes.
Play begins from an authored revision and selected save context; stopping it does not turn experimental actions into canonical design.
Promoting a selected Play result creates an explicit authoring operation with causal references to the play events.
Rolling back or undoing an edit records the change of state; Adam cannot keep describing the undone result as current.
Queries combine historical records with current validated world state before suggesting an action.
A once-valid shortcut must not be described as currently open after a committed blockage or incompatible scene change.

For example, route.choice_committed can record route UUID, localized name key, chosen connection, and its branch/session context.
Only if that record exists and the current route still reaches the hub may Adam say: “You chose {recorded route name}. It still leads home.”
The localized name comes from that recorded route's valid content reference; the system does not invent a shortcut name.
Without recorded choice history, use a present-tense offer such as “We can trace a way back.”
A discovered hazard is remembered by its event/entity identity and current status, not by an unsupported model recollection.

## 5. Logical state and durable checkpoints

A repair command can logically succeed before its checkpoint has committed to disk.
World-stable means the accepted repair, derived capacity, objective changes, and required logical consumers agree on the published state.
ADAM-FB-009 acknowledges that world-stable result; it is not a claim that a save has completed.
SaveService separately reports queued, committed, and failed checkpoint outcomes.
A saved/checkpoint-confirmation line may play only after the matching durable commit acknowledgment.
If storage fails, normal save feedback reports the failure while Adam's repair acknowledgment remains truthful about current logical state.

Persisted checkpoints reference a consistent chronicle position and the saved game-state revision.
A failed write preserves the last committed checkpoint and must not advance its durable chronicle marker.
In-session projections can include logical events pending persistence, with explicit durability status.
A restart cannot promise to recover an event that never reached durable storage.
On load, reject/reconcile inconsistent versions or references instead of inventing missing experience.
Automatic retry policies must not duplicate event IDs, completed objectives, or cue completions.

## 6. Opening cue beats

These trigger names and cue IDs are shared with adam_first_boot_contracts.json.
All trigger predicates are proposed game contracts; receiving an event name alone is insufficient without validating its current preconditions.
The two creator-selected canonical game lines below remain exact; their status is authored story dialogue, not authenticated historical speech.

| Cue ID | Trigger and required state | Authored dialogue / intent | Audio and optional haptic | Repeat/suppression |
| --- | --- | --- | --- | --- |
| ADAM-FB-001 | firstboot.control_ready; new-game control active; first contact unseen. | “I’m here. Start with what still responds.” | Close steady voice above low room ambience; one soft anchor pulse. | Once per new-game branch; ordinary reload does not restart the introduction. |
| ADAM-FB-002 | power.source_powered; first source's false-to-true change has committed. | “One circuit… responding.” | Actual fan/electrical state rises; restrained confirmation tap. | Once for that source; rejected interaction never produces this cue. |
| ADAM-FB-003 | fault.capacity_loss_visible; sustained visible loss threshold; fault remains undiscovered/unrepaired. | “Capacity… falling. Follow the loss.” | Descending conduit tone and visual trace; optional uneven pulse pair. | Once; suppress after discovery/repair or if loss no longer exists. |
| ADAM-FB-004 | fault.discovered; valid inspection committed discovered state. | “This line. Beneath the grate.” | Localized grate sound, visible clue, caption; soft tap optional. | Once per fault discovery; invalid targeting produces no diagnosis. |
| ADAM-FB-005 | trace.route_recorded; trace objective and route anchor committed. | “I have the route now. Take it when you’re ready.” | Stable return motif; optional soft anchor pulse. | Once; cancel if route/target/session becomes invalid. |
| ADAM-FB-006 | hazard.entered; BS enters the active fault's validated hazard boundary. | “Step clear. It’s pulling through here.” | Short caution motif; optional two distinct pulses. | Danger priority; cooldown plus meaningful re-entry; suppress after repair. |
| ADAM-FB-007 | repair.started; repair target and player preconditions accepted. | No spoken line; give BS room to act. | Restrained progress rhythm follows actual progress; optional low pulses. | Stop on cancellation; effect completion is not a heard dialogue line. |
| ADAM-FB-008 | repair.interrupted; progress had begun; fault still valid and unrepaired. | “We can come back to it.” | Progress rhythm stops without punitive flourish. | First interruption only; suppress during danger, unload, or target deletion. |
| ADAM-FB-009 | repair.world_stable; repaired state and dependent logical changes published. | “That connection holds. We can build from here.” | Stable machinery rhythm, resolving tone, optional soft confirmation. | Once per repair; never for attempted/failed repair or as disk-save confirmation. |
| ADAM-FB-010 | region.hub_returned; first post-repair return; traversed route/choice recorded. | “We know this way now.” | Return motif becomes part of hub ambience. | Once for this return milestone; later recall uses actual recorded choices. |
| ADAM-FB-011 | workspace.capability_restored; corresponding real workspace capability committed available. | World: “We can hold an idea here before we build it.” AI: “Bring me an idea. We’ll give it a shape.” | Quiet terminal wake-up; optional tap; available interaction appears. | Each supported capability once; no automatic forced opening or fictional unavailable tool. |
| ADAM-FB-012 | region.horizon_entered; BS voluntarily reaches overlook; next route is available. | “That route reaches beyond this room. You choose where we go.” | Distant sector motif enters room ambience; minimal haptic optional. | Once per milestone; expire if BS leaves or destination availability changes. |

Capacity thresholds, dwell times, cooldowns, expiry, and motif parameters belong to validated cue data and measured tuning.
A remembered route means its factual observation is recorded logically; durability is separately tracked until checkpoint commit.
Narrative language may gain historical context only when a relevant authored archive or recorded event becomes available.
The new context enriches the stable anchor rather than changing Adam into a different character.

## 7. Cue scheduling and heard-state semantics

Priority is danger > confirmation > guidance > lore.
Normal speech respects the proposed minimum interval; urgent danger may interrupt lore.
Each queued cue carries session/load epoch, branch position, target IDs, relevant preconditions, and expiry.
Revalidate before playback and before applying a gameplay-facing highlight or objective suggestion.
Skip stale, duplicate, unavailable-target, or incompatible-state cues instead of announcing obsolete outcomes.
An interrupted line is not recorded as fully heard.

Track cue attempts as queued, started, completed, interrupted, suppressed, or dismissed, with the reason and source event.
Completed delivery requires the configured audio clip or caption presentation to finish; it is system delivery evidence, not proof of human hearing. User dismissal records separate acknowledgment and may end repeat eligibility without claiming completed delivery.
Suppression is a scheduling outcome, not automatically permanent completion; eligible important guidance may be retried under its repeat policy.
Nonverbal progress effects maintain separate lifecycle state from speech heard-state.
Repeated failures produce diagnostics and useful fallback presentation without a tight retry/chatter loop.
Once-per-branch completion must survive valid checkpoint reload according to the active timeline.
A save failure cannot silently claim that newly completed heard-state is already durable.

## 8. Audio, tactile design, and cleanup

Adam's voice remains intelligible and spatially anchored; world transmissions may arrive as short fragmented diagnostic packets.
The interface keeps subtitles/transcripts and objective/clue visuals available independently of spoken delivery.
Sound motifs distinguish anchor, loss, return, danger, and resolution without demanding loud or startling effects.
Haptics are optional design motifs, capability-checked through the platform adapter; no controller or tactile hardware support is claimed yet.
No clue, hazard meaning, timing requirement, or successful action is communicated only through touch.
Provide disable/reduce-haptic controls and equivalent visual/audio feedback.
Pause, focus policy, controller disconnect, target deletion, session stop, and shutdown stop or suspend tactile effects predictably.
Resume revalidates cue state rather than replaying stale pulses or an obsolete line.
Volume/ducking and accessibility settings apply to cues without disabling Adam's continuity record.
A silent presentation mode retains textual guidance and factual memory.

## 9. Restoration lore and authoring bridge

Restoring a map/planning capability can reveal World Workspace; restoring a supported creation capability can reveal AI Workshop.
These are authored interpretations of actual capability/job events, not substitutes for engine state.
Restoration lore should make creating AI-BS feel continuous with exploring it while keeping technical diagnostics accessible.
The first opening may show a dormant terminal; it cannot announce a functioning tool that its release does not implement.
Entering either workspace retains project, selected entities, relevant history, and pending-job context.

Adam frames the actual authoring lifecycle: queued, running, artifact_ready, validated, applied, durable; failed and cancelled remain distinct outcomes.
Queued means accepted for work, not generated; artifact_ready means a candidate exists, not that it was validated or installed.
Validated means its declared checks passed; it is not a statement that scene changes or compiled code have already been applied.
Applied means the relevant scene edit or source/publication step succeeded; durable requires the matching persistence acknowledgment.
For code work, build success, new-session preview, file publication, and persistence remain separate reported facts.
Generation summaries reference job/artifact/operation IDs so creators can open the underlying evidence and diagnostics.
Adam can offer the next useful action without hiding failures behind successful-sounding restoration dialogue.
Preview and automatic-apply behavior remain configurable; this architecture adds no mandatory per-edit approval gate.
The editor's authoring authority does not transfer to an in-game NPC, script, or runtime AI proposal.

## 10. Proposed acceptance checklist

- Without any language model or authoring service, First Boot retains Adam's core records, authored cues, route/hazard recall, gameplay, and saves.
- Unload/recreate AdamAnchor entities and change regions without losing core identity or valid continuity.
- Replay a recorded meaningful choice and retrieve its original event ID; generated summaries cite that record.
- Record a shortcut choice and later use its real label only when the active branch/current route validates it.
- Load an earlier checkpoint and demonstrate that abandoned-future events are retained historically but absent from current-world claims.
- Undo an authoring edit and stop a Play session without promoting their superseded outcomes into canonical current memory.
- Force repair interruption/rejection and verify ADAM-FB-009 never plays before repair.world_stable.
- Delay/fail checkpoint storage: repair acknowledgment may play, saved confirmation must wait, and the last durable checkpoint remains identifiable.
- Interrupt, suppress, complete, and dismiss cues; verify their heard/retry policies differ and survive the correct checkpoint boundary.
- Expire a target/session while a cue or generation job waits; stale output never narrates or mutates the new world.
- Disable/disconnect haptics and pause/stop sessions; all information remains accessible and no tactile effect continues orphaned.
- Exercise every authoring job state and open its technical diagnostics from Adam's summary.
- Create a second project using neutral AIBS::Adam contracts without First Boot lore or shared player-history leakage.

All acceptance items require future executable tests and native/manual evidence appropriate to their behavior.
This document changes planning only; it performs no source edits, installs, builds, services, migrations, or runtime tests.
