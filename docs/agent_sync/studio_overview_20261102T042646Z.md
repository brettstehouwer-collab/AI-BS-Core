# Studio overview pilot — native and web

Requirement UI-OVERVIEW-001: apply the reviewed zinc/cyan/violet design to the
existing Studio landing page first, while the game-development task continues.
Decision: ACCEPTED by the user's request; targeted source integration VERIFIED.

The landing route remains `executive_cockpit`. Native still uses
`ExecutiveCockpitFullView`; web still uses `ExecutiveCockpitTab`. The route
registries, application shells, service adapters, polling, governance decisions,
chat payloads, action handlers, database state and trading controls are preserved.

The old four-column layout becomes a two-column card grid, stacking on smaller
windows. Scoped tokens supply zinc surfaces and cyan/violet accents, readable
text and controls, visible keyboard focus, and the web's existing Mom Mode.
Native Mom Mode retains its existing separate simplified workspace.

Only regular widgets in this view receive QSS. No application-wide Qt stylesheet,
window flags, DPI policy, DWM setting, custom viewport, or game input is changed.
The frozen native build can follow a static import of generated Python QSS;
the stylesheet does not depend on a missing external file at executable runtime.
Web component, CSS and token files are identical across all four existing mirrors.

Two defects exposed by rollout were fixed:

- Web chat auto-scroll moved the entire new page past its heading. It now scrolls
  only the transcript. The page opens at its heading; chat auto-scroll remains.
- Qt recovery's application event filter could receive a close event after its
  Python owner was released, raising an exception inside a Qt callback. A focused
  failing test reproduced the missing-owner error. A guard now ignores released
  Python/C++ owners; live-window close/save checks retain their behavior. The
  combined legacy regression suite passes after this fix.

A reflow queued before native shutdown also now exits before touching destroyed
content. Narrow-window action/status rows were corrected during layout testing.
The web version label now uses the existing repository version export. Static
spend and vault-count claims in labels were removed without changing their actions.

Verification against canonical source:

- 5 new overview tests; 17 executive service/view/recovery tests; 14 chat recovery
  tests; 6 web truth/mirror tests: 42 focused tests passed.
- 495 native layout checks across 100%, 125%, 150%, 175%, 200% scaling and
  600–1440 logical-pixel widths; 210 web checks at those scales, 320–1440 CSS pixels,
  normal and Mom Mode. No measured horizontal overflow or clipped wrapped native
  labels/buttons. Existing native signal bindings and all 17 web event bindings
  are preserved. Actual service/recovery methods are unchanged except the owner guard.
- TypeScript `--noEmit` passes. Offline web bundle succeeds using installed tools.
  API responses, mutations and private recovery in these tests use explicit offline
  fixtures; no live actions, microphones, email, or trading were exercised.

The combined Qt run initially crashed during stylesheet application. Failed runs,
the baseline comparison, the exact event-filter traceback, and red/green evidence
are retained in the output records. No failing assertion was disabled or skipped.

Coordination: the other chat confirmed it owns the C++ engine/native adapters and
has no edits planned in these cockpit views/styles. All existing targets were
checked against their pre-change hashes before replacement. The canonical branch
and index were not switched, staged, or committed.

Delivery: source changes are applied in `C:\AI-BS`. The isolated review branch
retains the patch and tests. No running application/service was restarted, and
no Windows executable or Firebase release was built/deployed in this task. A
running packaged app and the hosted web release show the new look after their
next coordinated build/release. Broad shell/other-tab styling remains out of scope.

Records and preimages: `C:\AI-BS-UI-Preview-Output\overview`. The small archive
belongs in the existing `AI-BS Complete Audit 2026-10-30` Google Drive folder.
No dependencies, recordings, installed programs, models, or release trees were copied.
