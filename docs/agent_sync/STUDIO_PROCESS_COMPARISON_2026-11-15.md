# T06 owned-process AST comparison and first caller

Same immutable engine.py SHA256 as retained thread baseline;64tasks,8AST parses
per task. Existing unchanged ProcessBatchController/JobSpec/OwnedProcess used,
eight-job cap, explicit recovery Python -I/-B children,10s job deadlines and1KiB
retained output. Batch pacing configured only on this disposable controller:
start interval0, batch size64, cooldown0; its existing15ms dispatch timer remains.
No production settings, scheduler/security primitives or existing tests changed.

One measured run:1055.968ms elapsed including child startup/pipe drain;211timer
samples at5ms nominal interval, p50 5.002ms/p95 5.185ms/max5.689ms. All64processes
exited0, output index/hash/parse-count matched, all job events arrived on the GUI
thread and every job/controller drained. Observed active peak6, parent RSS peak
31,350,784bytes; child memory is excluded. Timer sampling can miss transient
peaks. Prior pool run:1470.943ms and max607.496ms timer interval. This is one
synthetic QCoreApplication comparison, not mounted-widget input latency, a
repeatability study or general production speedup. Workload dispatch/startup
differs between routes; do not infer guaranteed quotas or universal thresholds.

Evidence: backups/studio_process_comparison_20261115_v01/result.json, measure.py
and ast_child.py. Frozen native172 tests and live services are separate scopes.

## Selected first actual caller — proposed migration, not applied

native_studio/bs_chat_ide_full.py `_validate_syntax` synchronously calls
`compile(editor_text, '<scratchpad>', 'exec')` then displays a result. Select this
read-only caller before `/graph`, which writes the master database, or any model/
embedding operation. Preserve compile semantics: ast.parse alone does not reject
all errors compile rejects (for example return outside a function). Never exec
the candidate, import it or write it back to the editor/original file.

Implement a bounded owned syntax job over existing process lifetime controls.
First resolve the frozen-compatible worker entry/interpreter and private
snapshot/output ownership; do not assume a checkout Python exists in a portable
package. No arbitrary shell, model fallback or new scheduler. Source bytes remain
local; archive only hashes and synthetic cases. Bind result to task ID plus editor
snapshot digest/generation, reject stale results, show bounded diagnostics without
raw source/tracebacks, retain failed recovery evidence, and participate in the
existing normal-close/drain barrier. Cancellation is not completion until joined.

Candidate measurement budget (proposed, not guaranteed): <=1MiB UTF-8 snapshot,
one syntax job per editor,10s child deadline, <=4KiB result, nominal5ms heartbeat
with p95<=25ms and max<=100ms for the agreed synthetic burst. Revisit budgets if
representative mounted-widget measurement contradicts them; do not silently
truncate or claim support for larger input. Cover syntax success/error, compile-
specific errors, no execution, Unicode/encoding, stale results, cancellation,
timeout, private snapshot failure, normal close and package independence within
a10–15assertion smoke profile. Preserve existing broader release gates.

Next resolve existing helper/packaging/lifecycle contracts for this caller and
make a focused compatible adapter. General workspace fairness/progress/task
envelopes remain proposed. Full ten-goal/six-addition goal ACTIVE/incomplete.

Five-member engineering Drive archive downloaded byte-exact and all member
hashes verified; sharing unchanged, private records excluded. Receipt:
backups/studio_process_comparison_20261115_v01/engineering/drive-verified.json.

Bounded integration inspection: MainWindow already shuts down and waits for
bus._process_batch_controller; shared_batch_controller(bus) reuses that owner.
Existing registered native_source_check.py uses ast.parse and therefore cannot
silently replace scratchpad compile semantics. Terminal's packaged helper still
requires external recovery Python; a standalone worker entry must be resolved
explicitly for this new caller. No helper/primitive was patched during inspection.
