# Studio task concurrency review and proposed extension

Status: **REVIEWED_PROPOSED_NOT_IMPLEMENTED**. Reviewed November 14, 2026 against branch `codex/audit-v532976-20261031`, HEAD `64fad2871e0a716d9964f506bdef1050612b173d` and the current dirty source. This document adds an architecture proposal. It authorizes no implementation, provider request, service activation, deployment or package promotion. `ready_for_execution` is **false**.

The proposed generic worker pattern is useful, but Studio already implements its core. Extend `native_studio.engine.Task` and `EngineBus` through compatible adapters. Preserve their shared admission controls, GUI delivery fence and actual pool-drain ownership. A second worker framework or independent pool for every tab would split those controls and make aggregate resource use harder to bound.

## Current implementation and namespace

The actual package is `native_studio`. `ai_bs_studio/`, `ai_bs_studio/core/` and `native_studio/core/` are absent. Current source entries include `native_studio/app.py`, `native_studio/bs_chat_ide_full.py` and `native_studio/work_controls_app.py`; the terminal is `native_studio/ai_bs_ide_terminal.py`. The supplied `ai_bs_studio/core` destination must therefore be corrected before implementation. If a future extraction needs a `native_studio/core` package, it requires an import/packaging migration; this review creates no package and proposes no immediate file move.

| Verified source | Reuse | Gap to address through a proposed extension |
|---|---|---|
| `native_studio/engine.py:76` — `WorkerSignals`, `Task`, `_TaskRelay` | Background callable, result/error/finished signals, explicit queued GUI slots, cancellation delivery fence, `setAutoDelete(False)` | No task ID or progress contract; errors are strings; the callable does not automatically receive the cancellation event. |
| `native_studio/engine.py:143` — `EngineBus` | Shared pool; default cap 8; queue cap 4,096; pause, pacing and batches; retained runnables; native join before release | No workspace fairness or task-specific owner/revision authority. `TASK_TIMEOUT_S = 5400` is declared but is not enforced by `Task.run`. GUI-thread admission assertions should be qualified before wider reuse. |
| `native_studio/process_batch.py:42` — `JobSpec`, `ProcessBatchController` | Job IDs, explicit executable/arguments, bounded deadlines/output, cancellation, failure halt and owned Windows process drain | IDs are batch-scoped; no workspace/revision envelope or per-job public progress protocol. Preserve its process ownership boundary. |
| `native_studio/ai_bs_ide_terminal.py:176` — `AIBSTerminal` | Asynchronous QProcess transport, serial queue, incremental output, helper/shell completion and shutdown | Command tuples lack a common task identity and revision context. Do not replace this transport with a blocking runnable. |
| `native_studio/app.py:1170`, `native_studio/work_controls_app.py:51`, `native_studio/native_creative_entry.py:34` | Close waits for the applicable pool, process and terminal barriers while retaining owners | New tasks must participate in these existing barriers; a worker's `finished` emission is insufficient proof of native return or child drain. |
| `native_studio/local_refactor_view.py:142`, `native_studio/screenwriting_view.py:2607`, `native_studio/bs_chat_ide_full.py:1586` | Existing submit callers for proposals, writing and retrieval | Inventory each caller's cancellation, context and commit contract before migrating it. This was a bounded source review, not a complete call-site or provider audit. |

`native_studio/AI_BS_Studio.spec:29` targets the actual Studio entry and package imports. Frozen artifacts and source remain separate qualification surfaces. The current reviewed local runtime receipt records Python 3.12.14 and Qt/PyQt 6.11.0 in `backups/resume_20261114_creative_qualification_v01/probe-result.json`.

## Qt/Python constraints used in this review

Keep widget access on the GUI thread. Deliver worker events to a GUI-owned QObject with explicit queued connections and decorated PyQt slots; the receiver's event loop and thread affinity govern delivery. Avoid direct widget callbacks from a runnable. Create and dispose QObject owners in the correct thread, with QApplication alive through teardown. These requirements follow Qt's [Threads and QObjects guidance](https://doc.qt.io/qt-6.11/threads-qobject.html).

Retain the current non-auto-deleting runnable ownership and pool barrier until a separately tested replacement exists. Qt documents default automatic deletion, a race when reusing an auto-deleting runnable, and queue-removal ownership considerations. A pool destructor can block; window close must continue using the existing nonblocking stop-and-drain protocol. See [QRunnable](https://doc.qt.io/qt-6.11/qrunnable.html) and [QThreadPool](https://doc.qt.io/qt-6.11/qthreadpool.html).

A QRunnable provides a task body, not an automatically running event loop for arbitrary asynchronous QObjects. Keep the existing QProcess transport on its owning event loop. If a future long-lived worker needs Qt timers or sockets, review a QObject/QThread event-loop design separately. Do not use GUI-thread `waitForFinished` or polling loops as a substitute for asynchronous process signals. See [QProcess](https://doc.qt.io/qt-6.11/qprocess.html) and [thread event-loop guidance](https://doc.qt.io/qt-6.11/threads-qobject.html).

Moving Python work to a thread can preserve responsiveness, but it does not establish multicore speedup for CPU-heavy Python on this CPython 3.12 runtime. Use measured native extensions or the existing owned-process boundary for large pure-Python AST work where appropriate. Threads remain suitable for bounded blocking I/O. See the [Python 3.12 threading/GIL documentation](https://docs.python.org/3.12/library/threading.html).

Version scope: the Qt links target the 6.11 documentation family; retrieved pages may describe a later 6.11 patch than the installed 6.11.0 runtime. No new patch-specific API is required by this proposal. The official [PyQt6 signals/slots page](https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html) could not be retrieved in this session. No PySide-specific behavior is substituted for an unverified PyQt guarantee; binding-specific ownership and signal-object behavior remain explicit acceptance tests.

## Proposed task contract

Preserve existing `submit(fn, *args, on_result=..., on_error=..., **kwargs)` callers and their current result-object, string-error and no-argument-finished signals. Add an opt-in task adapter rather than silently changing those signatures.

The adapter would carry a versioned task record with an opaque task ID, workspace/owner binding, operation, request generation, expected source revision/hash, resource class, cancellation event and bounded deadline. IDs identify work; they confer no authentication or write authority. Capture context at submission and revalidate it both before dispatch and before any commit. Existing screenplay owner/CAS fences, editor pre-write journal, SQLite authority and isolated Chroma storage bins remain authoritative.

Provide the requested result, error, finished and progress events through a new structured envelope keyed by task ID. Proposed progress includes a monotonic sequence, stage, completed units and optional total; indeterminate work must not invent a percentage. Freeze/copy the small event payload before emission and never mutate it afterward. Deliver it through a GUI-owned queued relay that rejects cancelled, retired-workspace or superseded-generation events.

Progress injection is opt-in: an adapter passes a documented callback or task context only to a callable declared to accept it. Existing keyword arguments must not be overwritten, and an arbitrary callable cannot acquire real progress merely by receiving a callback. A cooperative callable must inspect its cancellation event between bounded work units. A thread cannot be forcibly killed safely because a deadline or flag expired.

The requested error tuple can be represented as `(exception_type_name, safe_message, bounded_diagnostic_text)` within the new envelope. Keep the legacy string-error path through an adapter. Do not retain live exception/traceback objects, locals, credentials or document contents in UI events. Public error text and private diagnostic detail require separate bounded policies. `finished` means the attempt reached its terminal path, not success; record success/failure/cancellation once and release native ownership only after the existing drain barrier.

## Workspace admission and workload placement

Treat a workspace pool first as logical admission over the existing EngineBus, with one aggregate cap. Preserve the current cap and behavior until measurement supports a change; do not multiply an eight-thread pool by the number of tabs. Give each workspace bounded queued work, fair admission and a cancellation generation. Keep external backend/GPU/provider schedulers independent and respect their existing contracts.

| Work | Proposed route and resource boundary |
|---|---|
| LLM requests and streaming | Existing authenticated client/provider path; offload bounded blocking client work or reuse its asynchronous transport. Keep provider/model ownership, cancellation, no-replay rules and backend GPU admission. No generic worker may activate a model or add fallback. |
| Chroma retrieval/indexing | Existing storage-bin and principal scope; bounded read/index batches. Create/use clients according to their verified thread-safety contract; do not share a connection or global owner state by assumption. SQLite remains the relational/provenance authority. |
| AST/code inspection | Immutable source snapshot and expected digest; small bounded work may use the pool. Profile larger CPU-heavy work and use registered owned child jobs when isolation, parallelism or a hard cancellation boundary is needed. A result never automatically applies a patch. |
| Process jobs and terminal commands | Existing JobSpec/OwnedProcess/ProcessBatchController or QProcess helper path; retain exact executable, deadlines, output caps and child/helper drain evidence. Do not wrap an already asynchronous QProcess merely to consume another pool thread. |

Prototype budgets must include aggregate active work, per-workspace queues, queued bytes, output retention, progress frequency, deadlines and GPU/provider admission. Candidate measurement settings are at most 10 progress updates/second/task and a small bounded event payload, with coalescing of intermediate progress and guaranteed terminal delivery. These are proposed starting points, not installed limits. Worker caps are admission controls, not hard CPU/GPU utilization quotas. Preserve the existing two-strike process/terminal failure halt.

## Proposed phases and acceptance gates

1. **Contract and baseline:** inventory one harmless read-only caller; define task/error/progress schemas and context fences; measure current event-loop delay, queue depth, memory, task duration and shutdown time. Confirm package/import ownership and compatibility before choosing a module location.
2. **Compatible adapter:** add opt-in task context, progress and safe error translation over the current Task/queued relay. Keep all legacy callers and lifecycle behavior. No engine replacement or package move in this phase.
3. **Workspace admission:** add logical workspace quotas/fairness and targeted cancellation without exceeding the shared cap. Progress coalescing must prevent queued-event floods. A deadline reports cancellation requested until actual completion/drain is established.
4. **Synthetic qualification:** use injected functions, temporary stores and owned harmless children. Assert GUI slot thread identity; result/error/progress ordering and bounded payloads; exactly one terminal outcome; queued cancellation with no run; cooperative running cancellation; stale owner/revision results denied; late events after view disposal ignored; active and queued owners retained until real join; no model request or private-store mutation. Exercise progress floods and exceptions, including cleanup failures. Keep existing EngineBus shutdown, process and creative regressions.
5. **One-caller migration, then separate release review:** migrate the harmless read-only caller first. Introduce LLM, Chroma, AST and process integrations individually only within their authorization and data contracts. Reconcile shared-engine/creative dependency pins after any relevant source change; repeat scoped source/runtime tests and the separate normal GUI lifecycle gate before manifest or package promotion.

There is no measured basis for a sub-millisecond responsiveness promise. Record reproducible workload, hardware/runtime versions, event-loop delay distributions, worst observed stall, queue/memory peaks and drain times; select acceptance thresholds from that baseline before implementation. The earlier current-runtime synthetic tests are reuse evidence, not validation of this unimplemented task extension or the outstanding normal creative-close/browser gates. No `ready_for_execution` or completed-performance claim is made.

Next executable step remains a separately authorized contract/baseline phase. This review changes only this Markdown file and its paired JSON record.
