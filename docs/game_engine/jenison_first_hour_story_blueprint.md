# Jenison enemies and first hour story blueprint

Status: PROPOSED narrative and systems planning. No game build, runtime test or manuscript edit.
Source: Echos Within Structured Edition, selected character and memory passages, plus the creator's directions. Source locators below use section titles and internal extracted paragraph indices, not printed page numbers. The cast is a supported starting inventory, not an exhaustive identification of every negative figure in the manuscript.

## Canon and adaptation

Jenison is the unwanted starting district, full of opposition to BS. The shelter and Pencil Room are places he establishes within or beyond that environment. Adam is the creator's remembered brother and safe person; his warmth and support remain steady through different paths and outcomes.

The manuscript supplies its author's account of relationships and experiences. Enemy titles, territory control, machines, combat behaviors, quest situations and alternate outcomes below are newly proposed fiction. They are not additional allegations or historical dialogue. Preserve aliases and source ambiguity rather than inventing an identity. Do not turn every difficult relationship, fellow child or person mentioned in a painful passage into an enemy automatically.

## 1. Source-based antagonist map

| ID / source figure | Manuscript basis | Proposed Jenison role | Encounter and optional quest | BS choices and changed outcomes |
| --- | --- | --- | --- | --- |
| EN-01 Maverick | Lost So Much Time; Adam's Turning Point; The Mirror of Rage; paragraphs 48, 51, 54, 64. The author describes fear, anger and being afraid to ask questions. | The Controller: controls the main distribution gate and imposed district permissions. | Ask Anyway: restore a public inquiry terminal whose requests are being blocked. Hints reveal a maintenance bypass, an alternate power source and a way to challenge the gate's authority. | Confront the gate in an action encounter; expose its contradictory control records; bypass with a player-built supply line; or leave its territory through another route. The gate may be disabled, lose influence, remain isolated or become a later obstacle. Adam's support does not depend on choosing confrontation. |
| EN-02 Garry / Lane | Justice and Perspective, paragraph 66 explicitly links the names; paragraph 123 discusses Garry. Relationship and alias details need careful source reconciliation before a full biography. | The Sealed Custodian: a fictional keeper of restricted archive access. Exact character name remains Garry/Lane pending alias selection. | A Door on Your Terms: locate a catalog fragment and establish an independently controlled archive entrance. The quest concerns present access and boundaries rather than mandatory reenactment of a source event. | Secure records through the Archivist, build a separate entrance, disable the custodian's permissions or defer this area. Changes affect archive access, retained keys and later encounters. Essential progression has another route. |
| EN-03 Unnamed school authorities | Truth When I Found, paragraphs 1060-1061: the author's account of being refused a call and punished after forgetting he had already asked. | The Denial Desk: a proposed composite authority NPC and rule system, not an invented named individual. | A Line Home: reconnect a communication terminal and open a route for requests. The NPC knows about a service conduit but initially withholds access. | Repair the official channel, reroute it, negotiate using completed work or construct a new relay. Outcomes change communication reach and future visitor access. Filing a request is an optional route, not a demand to seek this NPC's approval. |
| EN-04 Unnamed transactional acquaintances | Lost So Much Time and Adam My Brother Always, especially paragraphs 49, 283-291: the author's descriptions of conditional interest, disappointment and people withdrawing. No single named identity established here. | The Conditional Brokers: an explicitly fictional composite faction trading in access, favors and parts. | The Price of a Favor: examine a component offer with a future obligation; find a salvage or construction alternative. A broker's information can be useful while their offer remains optional. | Accept a clearly stated trade, negotiate, fulfill and end an obligation, refuse, share supplies through another NPC or build the missing component. Changes affect debt records, prices, supply routes and who visits. Refusing does not end the game. |

Maverick and Garry/Lane are the named antagonist sources established by this reading. The latter two rows are labeled composites of described experiences. Add other named characters only after locating their passages and distinguishing their role. Supportive family and friends retain their own identities. A painful scene alone does not establish an antagonist classification.

Every interactable enemy NPC has contextual information, a side-quest offer or a response to completed/declined work. Hints can also be found through inspection, Adam's interpretation of visible evidence or other NPCs, so interacting with a hostile figure never becomes the sole way to proceed. Hostile combat units carry readable behaviors and recoverable clues rather than conversation requirements during combat.

## 2. Editable room and route diagram

Proposed relative layout; adjacency is authoritative, physical dimensions remain to be designed. The secured foothold is a small refuge inside the starting district. An outer shelter location remains a later alternative.

~~~text
J0 UNWANTED ARRIVAL STREET ---- Z-A ---- J1 DENIAL DESK
  | D01                                  | D02 / communication route
J2 SERVICE YARD ----------------------- J3 MACHINE BAY
  | D03 / hidden threshold               | D04
H0 SECURED VESTIBULE ----------------- H1 SHARED LIVING SPACE
  | D05                                  | D06
H2 PENCIL WORKTABLE ------------------ H3 PENCIL ROOM -- D07 -- A0 ARCHIVE EDGE
                                         |
                                        D08
                                     H4 OVERLOOK
                                         |
                                      Z-B / bridge
                                         |
J4 BROKER WALK -- D09 -- J5 CONTROL GATE -- Z-C -- CORE SINKS

Alternative: J3 -> player-built lift/tunnel -> Z-C
Alternative: H4 -> player-built bridge -> A0
~~~

Doors and route zones have stable IDs. A door's open state, lock policy and removal are separate attributes. Opening D01 does not itself make all connected rooms safe. Completing the foothold's defined safety conditions establishes H0-H3 as dependable shelter; aggression and hazardous experiments stay in declared encounter/test zones.

| Room | Editable elements and anchors | Entry/interaction rules |
| --- | --- | --- |
| J0 Arrival | D01; initial route marker Z-A; cover and movable debris | First arrival establishes Jenison's opposition; entering alternate zones changes discovery order |
| J1 Denial Desk | D02; communication socket S-COM; Denial Desk NPC anchor N-DESK | Requests, inspection and relay construction supply alternate ways forward |
| J2 Service Yard | D03; salvage sockets S-SAL1/2; Courier anchor N-COUR; service crossing Z-SERVICE | Crossing reveals an engineering route; salvage ownership/policy is displayed |
| J3 Machine Bay | D04; supply S-IN; consumers S-LAMP, S-ARCH, S-LIFT, S-PLAY; machine pads P1/P2; Tinkerer N-TINK | Built machines publish valid power/collision before unlocking dependent capabilities |
| H0 Vestibule | D03/D05; safe-return anchor Z-RETURN; Caretaker N-CARE | Safety becomes active through explicit conditions; returning refreshes current guidance |
| H1 Living space | D04/D06; movable seats SEAT-1/2; shared-play device; visitor anchors N-VIS1/2 | Sitting and play are optional moments of familiarity; rearrangement updates navigability |
| H2 Worktable | Pencil/tool anchor; lamp S-LAMP; writing seat SEAT-DESK; record/trace/sketch surface | Inspect, preserve or sketch can each introduce different first tasks |
| H3 Pencil Room | D06/D07/D08; shelves SH1/2; display anchors MEM1-4; archive console S-ARCH; Archivist N-ARCH | Moving shelves can expose a maintenance panel; reading personal material remains optional |
| H4 Overlook | D08; seat SEAT-VIEW; Listener N-LIST; bridge endpoint B1 and route zone Z-B | A built accessible route changes visitor paths; horizon cue requires an available destination |
| A0 Archive edge | D07; bridge endpoint B2; catalog socket S-CAT; Custodian N-CUST | Catalog recovery, independent entrance or existing route can establish access |
| J4 Broker Walk | Trade counter, Broker N-BROK, parts storage and a public route | Offers show obligations and alternatives; accepted deals retain explicit terms |
| J5 Control Gate | D09; controller N-CTRL; authority terminal S-AUTH; supply nodes | Confrontation, records, bypass and departure branches evaluate actual current state |

NPC anchors define initial meeting/work areas, not permanent immovable positions. Their schedules use reachable paths. Moving a chair, removing a door or placing a machine triggers reference, collision and route checks. Structural edits remain possible through the shared building tools.

## 3. Selected personal-memory candidates

Selection below identifies meaningful source material for adaptation; it does not automatically publish full passages, recordings or photographs.

| Memory ID | Origin | Intended meaning | Proposed presentation |
| --- | --- | --- | --- |
| MEM-01 Pencil | Adam My Brother Always, paragraph 289 | Writing can preserve a relationship that possessions cannot replace | The ordinary pencil at H2 becomes Record/Trace/Sketch; a selected writing can remain private |
| MEM-02 Home | Paragraph 1065, the creator's description of home as wherever Mom and Adam lived | Safety comes through relationship and belonging | Warm thresholds and a dependable return place; no claim to reconstruct a specific real house |
| MEM-03 Adam's encouragement | Adam My Brother Always, paragraph 284 | Adam recognized and spoke about his brother's strengths | Optional reflection after a creation; newly written encouragement is labeled game dialogue |
| MEM-04 Shared gaming | Paragraph 62 and the gaming setup described in paragraph 288 | Ordinary enjoyment and time together | Optional shared-play corner; actual game/title/device selection remains open |
| MEM-05 Red toy truck | Paragraph 61's remembered happy moment | Laughter and affection have a place alongside difficult memories | Optional toy/model or small build inspired by the truck, without automatically recreating the surrounding painful scene |
| MEM-06 A smile and breath | Light In This World, paragraph 275 | Seeing Adam happy mattered deeply to the creator | A quiet place of warmth and shared enjoyment; no score measuring affection |
| MEM-07 Turning bad toward good | Whole Life Until God, paragraph 1047 | The creator describes learning this from Adam | Damaged machinery can be rebuilt for a useful communal purpose |
| MEM-08 Remembered safety with Adam | Paragraph 1066 | Familiarity, admiration and trust | Guidance and comfortable silence that remain steady through mistakes; personal sayings come from supplied memories |

Personal-memory records and fictional gameplay history stay separate. Building a bridge creates a game event; it does not create a new biographical memory. Family relationships are not reduced to collectible ranks or competing affection meters.

## 4. First-hour branch graph

Time windows are pacing estimates, not deadlines. Exploration, dialogue and building can change their duration and order.

~~~mermaid
flowchart TD
  A[0-10 min: unwanted Jenison arrival; Adam's first contact] --> B{Choose an approach}
  B --> C[Writing route: inspect desk and preserve selected writing]
  B --> D[Engineering route: enter service yard and build supply]
  B --> E[People route: speak with Courier or Caretaker]
  C --> F[Recover catalog clue; face or bypass Custodian]
  D --> G[Power archive, play space or lift first]
  E --> H[Help a delivery, decline a trade or reconnect communication]
  F --> I[Establish a secured foothold and choose its first purpose]
  G --> I
  H --> I
  I --> J{30-60 min: next departure}
  J --> K[Archives first: contextual knowledge and writing tools]
  J --> L[Core Sinks first: machines, resources and alternate power]
  J --> M[Network route: visitor connections and delivery access]
  K --> N[Return with distinct history, NPC follow-ups and new builds]
  L --> N
  M --> N
~~~

Writing-first can produce a catalog-led archive entrance and earlier personal context. Engineering-first can yield an independent supply line and greater construction flexibility. People-first can produce route knowledge and visitors before equipment expansion. All three retain access to the other paths later unless an explicitly signaled story decision changes a particular opportunity.

Further differences arise from source power choice, broker obligations, gate status, route built, NPC help and what is shared. Convergence on a refuge does not erase these facts. Adam can recall a route actually used and suggest currently valid options; he does not prescribe one correct way to honor his memory.

## 5. Rule, NPC and quest authoring contract

One shared project model serves visual tools, AI authoring and code. Each authored rule has ID/schema version, event type, subject/zone, preconditions, affected entities/cells, priority, effects, repeat/cooldown policy, reversibility, evidence/provenance and save migration requirements. Every relevant action type can be a rule input; an individual input does not require an individually scripted ending.

Movement rules use crossings, arrivals, dwell and ordered route steps. Door rules separate open/close, lock/unlock and build/delete. Construction rules separate candidate, validated placement, applied world state and durable record. Conversation rules consume current facts and record informed choices. Facts, relationships and quest stages have separate namespaces rather than a single morality score.

Example planning rule:

~~~json
{
  "id": "JEN.ROUTE.BRIDGE_READY", "schema_version": 1,
  "on": "construction.route_published",
  "when": ["endpoints B1/B2 connected", "render/collision revision admitted", "destination available"],
  "effects": ["enable player route Z-B", "mark Courier navigation dirty", "offer current delivery follow-up", "record Adam route memory"],
  "npc_route_ready_when": "matching navigation revision admitted",
  "repeat": "idempotent per route revision",
  "reverse_on": "route removed or invalidated",
  "durability": "world delta and semantic memory commit together"
}
~~~

Each NPC profile defines source identity/provenance, fictional adaptation layer, role, anchors/schedule, knowledge, current attitude, dialogue predicates, hint tiers, quest offers, completion/decline responses and unavailable-target behavior. Each named antagonist retains the manuscript alias map. A composite remains labeled as such.

Each quest defines offer conditions, stages, objective predicates, alternate methods, rewards/consequences, failure/defer states, dependencies, repeat policy and save version. Hints can progress from observation to location to method, with alternatives when a key object is gone. Every interactable NPC has a relevant hint, opportunity or acknowledgment appropriate to current state; procedural invention cannot silently replace a source person's biography.

Before applying an authored change, the creator preview shows: changed objects and doors; power consumers; reachable routes/NPC anchors; affected quests/hints; source-memory/dialogue provenance; undo cost; and save compatibility. Preview/autonomous draft application follows the configured creation workflow, not a new mandatory approval gate.

Changes use operation IDs and expected revisions. Duplicate committed operations return recorded results. Editing an active rule creates a new rule/content version. Existing saves either migrate through a declared mapping, retain their compatible content version or report a specific conflict. Never silently reinterpret an old quest stage under changed conditions. Branches retain content manifests, event heads and operation results; demolition invalidates dependent current facts while retaining historical records.

## 6. Predicted consistency walkthrough

This is a design walkthrough and future acceptance matrix, not executed testing.

| Scenario | Expected consistent result | Alternate progression / hint |
| --- | --- | --- |
| Open then close D02 | Current communication/route policy updates; discovery history remains | NPC explains the present closed route and identifies the service relay |
| Build then dismantle generator | Supplied capabilities follow actual wiring; dependent quests pause or reroute; parts follow declared policy | Caretaker points to another source or salvage route |
| Build bridge, use it, remove it | Player collision and routing invalidate coherently; recorded crossing remains historical | Courier uses reachable fallback or waits with a stated reason; Adam does not call it currently open |
| Move a shelf onto a doorway | Placement preview reports access impact; apply follows chosen world policy | Another exit, relocation or undo remains available for essential progression |
| Leave and return | Pending quests re-evaluate current world state; completed introductory hints stay completed | NPC acknowledges developments and offers current follow-up |
| Help then decline further work | Completed help remains recorded; follow-up becomes declined/deferred | No replay of the finished first task; other departures remain available |
| Decline Broker, then build part | No debt recorded; construction alternative satisfies compatible objectives | Broker reacts to actual independent supply; offer can change under explicit rules |
| Accept Broker, then repay | Obligation and repayment are distinct durable events; no duplicate charges on retry | Later terms follow declared profile and do not secretly resurrect settled debt |
| Enter Archives before restoring lift | Archive route remains usable if its own predicates hold | Machine quest changes to optional convenience rather than contradictory prerequisite |
| Repair before receiving quest | World-state objective is recognized when the offer is evaluated | NPC gives acknowledgment/follow-up, not a demand to repeat the repair |
| Save/reload each of three routes | Reconstruct doors, builds/deletions, debt, quest stages, NPC knowledge and Adam's applicable history | Same valid departure options or explained version conflict |
| Rewind checkpoint | Select/fork the saved branch; later outcomes stay archived, not current | Adam recalls only applicable current history unless explicit alternate-attempt lore is enabled |
| Change rule version on an existing save | Show dependency/compatibility differences before publication | Apply migration, retain compatible version or restore previous publication |
| Save fails after repair | In-session repair can be stable; last durable checkpoint remains identified | Separate save feedback; Adam never claims the new checkpoint was stored |

Future walkthrough evidence must include all three first-hour routes and combinations of door/machine/NPC changes. Record unreachable nodes, stale hints, duplicate costs and incompatible saves as failures requiring design correction.

## Next story decisions

Reconcile Garry/Lane's final alias and relationship before writing a full character biography. Review additional manuscript characters before expanding the named cast. Choose which personal-memory candidates enter the first hour, and select the foothold's visual references. Then detail antagonist encounter scenes and the first departure's later consequences. All such work remains planning.
