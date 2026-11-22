# Native148 candidate and Windows temporary-path repair

T01/T07 now has a fresh, consistently versioned native candidate. Managed source
metadata moved146→147 for the first fresh package, then147→148 for the diagnosed
Play compatibility fix. Both metadata preimage checkpoints remain under
`backups/release_versioning/`. Source148 is not hosted148: public Hosting146,
accepted Android1.0 and retained native144/145 remain distinct. Inconsistent146
and the unpromoted147 attempt are retained unchanged.

Windows reset left TEMP spelled `C:/Users/ADMINI~1/...`; Python resolves it to
`C:/Users/Administrator/...`. The native player's existing canonical-scratch guard
correctly rejects the alias spelling. Two owned expected-negative CLI probes
proved the alias fails that guard while the resolved path reaches content-format
validation; neither opens a window or touches a real save. The only application
code repair is resolving the newly owned ContentPlayClient temporary directory
before launch. Native guards, save/drain/cancellation and Win32 primitives remain
unchanged. No OS policy, profile path, ACL, environment registry or user data moved.

Fresh148 uses the existing bounded native builder, existing packaging Python and
previously qualified SDK/curated opening inputs. It includes the4324fca3… player
from the recorded controlled-motion candidate. Static verification passes: PE
version148, staged/frozen module equivalence,185declared inputs,429package files,
217,999,231bytes and reviewed package/privacy boundaries. This is not a semantic
security review of every dependency binary or a new SDK-source qualification.

The actual packaged early creator fixture passes all five workflow groups:
numeric Preview/Apply/Undo/Redo/Save/reopen, typed field transactions, DX12 numeric
and chapter previews with zero debug errors/warnings, deterministic QtNetwork
proposal admission and explicit Apply/Save, isolated native Play and normal save/
drain/close followed by matching saved-authoring reopen. Temporary gameplay data
is removed after owned processes join. No model inference, host-service startup
or real manuscript/save access occurred. This deliberately bypasses the broad
MainWindow; normal all-hub startup and actual user workflow remain unqualified.

The147 attempt passed static checks and four workflow groups, then exposed the
alias failure; its report, package, diagnostics and owned synthetic project remain
in place. All child processes joined.148staged input differences are only the
ContentPlayClient repair and version/release metadata. No passing test file or
frozen primitive was changed.

Existing default game/work launchers still target144 and BS-Chat retains its
existing launcher. `Launch-AI-BS-148-Candidate.cmd` is a separate explicit candidate
launcher, prepared but not executed; desktop shortcuts are not promoted. It opens
the normal Game Development entry when the user chooses it. Controlled early
fixture acceptance does not prove normal MainWindow/service behavior, ordinary
gameplay, human pacing/captions/likeness, current performance, signing/clean-machine
installation or full native/web parity. No manual gameplay test was requested.

Evidence: `backups/studio148_candidate_20261114_v01/`; retained147 evidence:
`backups/studio147_candidate_20261114_v01/`. All ten goals and six additions remain
ACTIVE/incomplete. Next qualify normal candidate entry and the combined browser/
backend rollout plan, while preserving live activation boundaries and private
backup requirements. No deployment, backend restart or default promotion follows.

Twelve core acceptance assertions pass against current managed versions, static
artifact identity and actual controlled runtime receipts. Separate Drive archives
are verified by exact downloaded bytes and every member hash/CRC:

-Source/handoff: `1Uk_6xH0GWZfD2H7x3LkruruxwRZJozA0`,926,217bytes/151members;
 receipt `backups/studio148_candidate_20261114_v01/source-backup/drive-verified.json`.
-Clean native runtime: `1BoKaAysXYSaaUIImYCKdTt9oV1zzomQg`,87,518,791bytes/432members
 containing all429package files and restore/qualification metadata; receipt
 `backups/studio148_candidate_20261114_v01/runtime-backup/drive-verified.json`.

Existing BS game parent/sharing preserved. No credentials, real saves, private
databases or manuscripts included; external services/weights and complete project
history are excluded. Byte/member verification is not relocated execution or
clean-machine acceptance.147failed package stays local with its evidence; the
reviewed failure/diagnosis is included in the source archive. Closing notes and
updated continuity pointers postdate the immutable archive snapshots.
