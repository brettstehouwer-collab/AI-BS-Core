# Managed Qt creator connection

`native_studio.game_engine.creator_client.CreatorClient` owns one `QProcess` and
uses the existing binary protocol against the actual `aibs_creator_host`.
It is the transport/controller used by the source Creator workspace described in
CREATOR_WORKSPACE.md. Installed Studio94 has not been rebuilt to expose it yet.

Create and use the client on its owning Qt thread. It starts only an explicitly
selected executable and existing workspace. It does not create folders, choose
player saves, scan the machine, save implicitly, or use EngineBus/startDetached.

```python
client = CreatorClient(parent_widget)
client.ready.connect(on_transport_ready)
client.response.connect(on_response)       # Python uint64 ID, immutable Response
client.request_failed.connect(on_failure)  # ID, reason; writes may be unknown
client.closed.connect(on_closed)
client.start(owner_executable, selected_project_directory)
```

The ready signal means protocol negotiation completed. Open the document with
`creator_commands.open_document` and `client.request(Opcode.OPEN, payload)`.
Then use the returned scope, head revision and schema to submit normal commands.
The client exposes `head`, `dirty`, `state`, `epoch`, `generation`, `process_id`,
`pending_count`, `queued_bytes`, `prepared_count`, and a bounded `stderr_tail`.
It does not interpret a successful transport connection as an opened document.

Request IDs remain unique across process restarts during this client lifetime.
Signals carry Python integers rather than Qt's32-bit int type. Responses must
match a pending opcode/ID, process epoch, document identity and monotonic head.
An old process object's callbacks cannot modify a reopened connection. A
duplicate operation may report an older operation revision alongside a newer
current head; the client never rolls the head backward to that receipt revision.

Each of these has an independent logical8-item/1MiB limit:

- Pending encoded request frames, retained until their matching reply.
- Original preview payloads retained behind prepared handles.
- Uncertain writes retained for explicit recovery, including admitted pending
  writes so a disconnect cannot exceed the recovery budget.

ApplyTransaction shares its immutable original payload rather than charging it
twice. ApplyPrepared retains the distinct original transaction as well as its
handle command. These limits are not exact RSS, Qt internal-buffer, response
cache, or caller-retained memory guarantees. Pipe reads are bounded to64KiB;
stderr retains only its latest16KiB. No unbounded readAll call is used.

`stop()` prevents new admission, drains pending replies, sends Shutdown once,
and reports closed only after Qt confirms the process has stopped. A deadline
forces termination and marks unresolved writes unknown. Normal stop is
asynchronous. The application's final aboutToQuit hook has a bounded wait/kill
fallback; normal UI code should stop and await closed before destroying owners.
Start is refused while the old handle is active or finalizing.

`abort(reason)` terminates an interrupted owner. `uncertain_operations` contains
immutable `RecoveryRequest` records with generation/ID/workspace/opcode/original
payload/revision and, where available, the exact original transaction bytes.
These records are **in memory only**. No automatic replay occurs. After reopening
the same saved world, decode the retained transaction, bind it to the new host
scope, and explicitly reconcile through ApplyTransaction with the original
transaction ID/revision/edits. Acknowledge a resolved record using
`acknowledge_recovery(generation, request_id)`.

History request identities are host-epoch-local and cannot be replayed as an
exact-once operation in a fresh host. Save/Play uncertainty also needs explicit
state inspection. UI code must manage unsaved document closure; this client
does not manufacture a successful save or persist a recovery journal itself.

All replies validate before a pending write is removed. Malformed acknowledgments
retain that write for recovery. A correctly framed rejection is a normal result,
not a successful edit. A view must publish rows only from valid pinned snapshot
pages and must not infer a finished chapter editor from this connection layer.

Evidence: `engine/tests/test_creator_client.py` runs against the installed native
owner. It covers real save/restart/history, queue budgets, graceful close,
interrupted prepared-edit reconciliation, late-generation guards, timeouts,
64-bit IDs, large valid payloads and Qt-thread ownership. One targeted protocol
fault is injected into the active real client to verify recovery retention;
it is not evidence that the native server generated that malformed reply.

The source AI-BS game-build workspace now includes explicit project metadata and
a selected-project browser, UUID outliner and grouped numeric inspector. Next:
editable chapter definitions and native Play processes. Native viewport/picking
now runs through the separately owned preview described in CREATOR_VIEWPORT.md.
Full M4 gates remain unfinished.
