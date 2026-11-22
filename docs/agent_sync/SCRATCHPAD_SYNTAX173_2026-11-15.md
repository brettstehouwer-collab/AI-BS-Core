# T06 scratchpad syntax source173

Scratchpad Syntax Check now submits a compile-only owned process through the
existing shared ProcessBatchController, replacing synchronous GUI-thread compile.
Source worker uses -I/-B; a fixed early frozen entry selects the bundled worker
before Qt/full-shell imports, avoiding an external interpreter requirement for
this operation. Frozen entry/package acceptance is still pending.

OneMiB UTF-8 maximum, one current batch,10s child deadline, <=4KiB validated
result. Existing controller output/deadline/admission/JobObject/close barriers
remain intact; no new scheduler or changes to those primitives. Fresh owner-
private operation directory and create-only source.txt preserve exact bytes.
Worker checks canonical non-reparse path, single-link/size and requested hash,
then compile only, never exec/import input. Compile semantics include rejection
of return outside a function. Invalid syntax is a successful validation result,
not a process failure or automatic retry. Diagnostics omit source/traceback text.
Snapshots remain local for recovery; no automatic deletion or total-store quota
is implemented. Same-account process ownership is not a filesystem sandbox.

Result waits for shared controller drain and validates snapshot identity. Editor
hash plus document revision rejects stale results, including edit/Undo to equal
text. New encoding-invalid editor text discards the old result. Busy, queued
cancellation and unavailable receipt paths retain editor/snapshot state. View
shutdown suppresses delivery; existing MainWindow stops/joins the shared owner.

13 focused source/real child/selected actual Qt-action checks passed, plus two
follow-up checks after the Unicode guard (one stale-action recheck, one encoding
guard check). No target execution, original file edit, model/provider request,
live database change, service restart, deployment or existing primitive/test edit.
Actual source full BS-Chat mounted lifecycle, representative performance budget,
timeouts/private-snapshot failure and frozen worker/package remain unqualified.
These scoped results do not establish all proposed concurrency features.

Files: native_studio/syntax_worker.py, syntax_check.py, app.py and
bs_chat_ide_full.py. Source173 metadata bump retains16preimages; previous app/chat
preimages are under backups/scratchpad_syntax173_20261115_v01/. Testing candidate/
launcher172, defaults144145 and last qualified web165/backend164/gateway52 stay
separate. Earlier172 and failed171 evidence retained.

Next full source mounted BS-Chat syntax action/close acceptance using synthetic
chat/media/recovery context and private synthetic editor text, then qualify the
exact frozen173 worker path before considering testing-launcher advancement.
No repeated stopped physical input or manual gameplay. Full original ten-goal/
six-addition goal ACTIVE/incomplete.

46member engineering archive downloaded from Drive byte-exact and all member
hashes verified; sharing unchanged, private snapshots excluded. Receipt:
backups/scratchpad_syntax173_20261115_v01/engineering/drive-verified.json.
