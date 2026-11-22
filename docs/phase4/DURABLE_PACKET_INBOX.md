# Retained packet inbox and current round-trip gate

Record122, October26,2026. Source/infrastructure verified; no project execution
authority or VM containment acceptance is issued by these components.

`isolated_workers/protocol/retained_inbox.py` retains a validated packet BLOB and
its `(worker,direction,nonce)` claim in one dedicated SQLite transaction. The
codec authenticates, canonicalizes and validates before invoking the callback.
The caller gets an accepted bundle only after the commit ends the owned
transaction. An uncertain acknowledgement can leave a committed row, which is
retained and rejects duplicate delivery. Inspection/recovery returns bounded,
hash-checked data and false-authority receipts; it never automatically replays
the packet or runs its contents.

The caller supplies an idle persistent private connection; the module chooses no
filesystem path. Exact schema, persisted quotas, a durable journal and FULL/EXTRA
synchronization are checked inside transactions. Existing/legacy stores are
refused rather than adopted. Caller transactions are not committed/rolled back.
Maximums are2MiB per raw packet,256rows and32MiB retained BLOB payload. These are
not total physical disk limits: SQLite pages/journals/metadata require additional
space. No pruning, live connector wiring, materialization, cancellation or
completed-transfer publication is implemented here. Filesystem/root authority,
runtime trust, leases and lifecycle enforcement remain broker prerequisites.

SQLite atomic commit relies on operating-system/hardware assumptions; these
tests do not prove universal power-loss durability. See
[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) and
[synchronous settings](https://www.sqlite.org/pragma.html#pragma_synchronous).

The project adapter now offers `inspect_vm_transfer` before collecting chunks.
It rejects unapproved output paths/sets and immutable metadata drift at that
stage, and checks private-store/model exclusions against original logical paths
before opaque mapping. Suffix rules are defense in depth, not arbitrary secret
content detection. The full20file/2MiB/16MiB/Unicode/dotfile/240character contract
is preserved for admitted data. All59combined infrastructure cases passed,
including full2MiB project-packet delivery through the new inbox and original
manifest reassembly, durable restart/replay/quota/schema/commit-uncertainty cases.

## Concrete first program

The private Number Summary package contains two Python files, an explicit test
specification, staging instructions and a manifest. Seven tests are specified,
not executed. The host only AST-parsed the sources and verified package bytes.
Private Drive metadata and exact downloaded cloud bytes match the host SHA256.
The signed-in integration guest reports five matching hashes and a fresh staging
directory. That report is an operator relay; the host did not directly inspect
its filesystem. All execution/apply/admission flags remainfalse andnot_run.

The confirmed workflow is BS-Chat program+test submission -> host validation
and bounded control-channel authorization -> separate clean disposable guest
tests -> validated files/logs/exit codes/results -> protected host preproduction
artifact comparison against original inputs and trusted tests -> independent
apply/deploy approval. A host quarantine folder is data storage, not permission
to run returned code. Any additional host-side execution requires separately
accepted isolation and host-issued authorization.

The reviewed AI-BS VirtualBox registry currently lists only the existing
AI-BS-Eval-Base-20261023 integration VM. This is a registry-scope finding, not a
whole-machine inventory. A separate execution guest is not registered there and
has not been accepted. Provision/verify its clean licensed image, standard task
identity, resource/network/filesystem boundary and lifecycle before dispatch.
The diagnostic18443protocol cannot convey the required job authority.

## Real host setup observation

The credentialed S4U task's complete definition and descriptor were checked.
Its fixed one-shot infrastructure diagnostic ran once, exited0, reported7/7
fixed access requests passing, and was disabled after submission. Its report
PID15868 matches the submitted task engine PID. It compiled only the fixed
probe and wrote a synthetic canary/report; no fixture program was run.

Independent QUERY-only primary-token observation failed with Win32error24 and
was not retried. The exact original failing stage was lost. Subsequent
self-token tests reproduced a compatibility defect specifically in TokenElevation
class20's zero-buffer sizing path. Direct4byte scalar queries and sanitized
stage/class/length errors repair that defect;10/10infrastructure cases now pass.
No corrected observer ran against the worker, so its independent token gate
remains open. The seven generic access requests do not prove granular
create/delete-child/protected-file/ancestor denial or any VM containment case.

All evidence, original source copies and helper provenance are retained under
`backups/durable_packet_inbox_20261026_record122`. The old one-shot orchestrator
and consumed entry must not be replayed. All fourteen actual VM containment
cases, live BS-Chat dispatch/collection, Phase5/6 and separate apply gates remain.
