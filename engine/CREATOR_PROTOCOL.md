# Creator protocol — development contract

Implemented: matching Python/C++ version1 framing, numeric edit payloads and a
native serialized owner process. The owner supports negotiation, Open/Describe,
bounded snapshot pages, Preview/Apply/Release, history, Save and in-process Play.
The managed Qt transport client is implemented and tested separately; see
CREATOR_CLIENT.md. The visual workspace, native viewport/picking, editable
chapter definitions and managed native Play child processes remain unfinished. Byte probes only
round-trip data; `aibs_creator_host` invokes the actual CreatorHost APIs.

## Framing

The 48-byte little-endian header is `magic[4], version:u16, header_size:u16,
opcode:u16, flags:u16, payload_length:u32, request_id:u64, epoch[16], revision:u64`.
Magic is `AIBC`, version1, header size48. Only flags0/request and1/response are
valid. Request IDs are nonzero. Frames allow at most4MiB payload; parser calls
accept at most64KiB chunks and return at most8 frames. Failure is terminal.
Callers must dispatch a returned batch only after the entire feed succeeds.
Per-read limits do not implement the planned8-request/1MiB pending queue.
Epoch negotiation and opcode-specific revision checks belong to the dispatcher.

## Numeric edit payload

All integers use little endian; strings use `byte_length:u32` then strict UTF-8.
Text allows at most4096 encoded bytes, excludes NUL, and never normalizes IDs.
Payloads allow at most1MiB. This is a separate bound from outer framing.

The payload contains, in order:

1. Payload version `u16=1`.
2. Project, branch, world UUID, host epoch UUID strings.
3. Original operation ID string, expected authored revision `u64`, description.
4. Edit count `u32`, followed by1–256 edits in submitted order.

Each edit begins with a one-byte tag:

| Tag | Fields in order |
| --- | --- |
| 0 / Create | alias, name, entity UUID, field count:u32, then field-name/binary64 pairs |
| 1 / Erase | alias, entity UUID |
| 2 / SetField | alias, field name, binary64 value, entity UUID |

Create allows at most64 fields. Duplicate keys reject. Encoders order fields by
name; decoders accept unique unordered fields and preserve their exact numeric
bits. Edit order remains unchanged. Values must be finite; signed zero remains
distinct at the creator-host retry boundary. Unknown tags, trailing data,
oversized counts, truncated strings and invalid UTF-8 reject before dispatch.

World and host epoch IDs must be lowercase canonical version4 UUIDs. Entity
UUIDs may be empty solely to preserve original legacy requests for host receipt
resolution. The codec does not invent missing IDs: CreatorHost still requires
explicit UUIDs for new operations and resolves accepted retries before live
target/revision checks. Codec acceptance does not establish world scope,
schema validity, target existence, capacity or permission to publish.

The dispatcher compares frame revision to the payload's original expected
revision, checks process/host epochs and document scope, then invokes the same
CreatorHost API as SDK calls. Persisted transaction retries and epoch-local
history retries resolve before live-head checks. Other scoped commands require
the current head revision. A duplicate reply carries both the original operation
revision and the separate current head revision.

## Native owner lifecycle and control commands

Launch `aibs_creator_host --workspace EXISTING_DIRECTORY`. Windows uses UTF-16
arguments. The process owns at most one opened document and writes only the
selected directory's `world.aibs` slot and the checkpoint store's associated
lock/temp files. Redirected slots/locks reject; this is project confinement, not
an adversarial-filesystem sandbox or a race-proof security boundary. No player
save path, current working directory fallback or memoir file is selected.

Stdout contains binary frames only; stderr carries bounded fatal diagnostics.
The owner reads exactly a header and its validated payload, allowing interactive
request/reply without waiting for stdin EOF. Incoming requests are capped at1MiB.
Framing errors/truncation terminate the connection; well-framed command errors
return structured rejection without invoking partial commands. Allocation or
response-pipe failure terminates instead of reporting a false rejection after
publication; the client must treat that outcome as unknown and reconcile using
original transaction IDs/reopened checkpoints.

Hello uses empty payload, zero process epoch and UINT64_MAX revision. A successful
reply establishes a fresh16-byte process epoch. Before negotiation, error replies
keep the zero epoch. Every later request must match the negotiated process epoch.
Repeated negotiation rejects. Open and Shutdown also use UINT64_MAX revision.

All control payloads except Hello/Shutdown start with version `u16=1`.
Scoped payloads then contain project, branch, world UUID and host epoch strings.

| Command | Remaining fields / behavior |
| --- | --- |
| Open | project, branch, create-if-absent:u8, schema count:u32, then name/minimum:binary64/maximum:binary64. Count1–64; no duplicate fields. Existing files must match scope/schema. Opening never implicitly saves. A second Open on this process rejects. |
| Describe | Scope only. Response body is schema count:u32 and name/minimum/maximum records. |
| SnapshotPage | Scope, checkpoint UUID (empty before first save), last alias (initially empty), limit:u32(1–64). Cursor is pinned to host epoch, frame revision and checkpoint ID. |
| ApplyPrepared / ReleasePrepared | Scope and opaque UUID handle. The server retains at most8 strong prepared references. Handles clear after publication/history/save; Release frees one unused handle. |
| History | Scope, caller request ID and direction:u8(0 undo,1 redo). Retry identities remain host-epoch-local. |
| Save | Scope only; stale revisions reject before filesystem work. The checkpoint store still verifies existing durable head identity. |
| StartPlay | Scope only; starts the existing isolated in-process World. |
| StopPlay | Scope and exact Play epoch UUID. No authored apply-back. |
| Shutdown | Empty payload; no implicit save. EOF likewise never silently saves. |

Prepared handles are not durable operation identities. If an ApplyPrepared reply
is lost, retry the original transaction through ApplyTransaction, preserving its
ID/revision/edits. The editor must explicitly manage unsaved-document closure.

## Structured response payload

In order: version:u16(1), status:u16, message text, host epoch text, project text,
branch text, world UUID text, current head revision:u64, checkpoint text,
original operation revision:u64, prepared-handle text, current Play epoch text,
save-compatible:u8, encoded-save-bytes:u64, save-assessment message text,
live entity count:u32, undo depth:u64, redo depth:u64, body length:u32 and body.
Document metadata is empty before Open. Save assessment is populated for prepared
changes; other replies may report `Not assessed` and zero bytes.

Wire statuses are explicit:0 OK,1 prepared,2 applied,3 duplicate,4 undone,
5 redone,6 saved,7 playing,8 stopped,100 rejected. They are not C++ enum ordinals.
Responses echo opcode/request ID, set the response flag and carry the current
head revision in the frame. Response bodies are limited to512KiB.

Snapshot bodies contain next-alias text, more:u8, entity count:u32 and entity
records (alias/name/UUID/field count/field-name/binary64 pairs). Pages fit both
the requested count and a500KiB entity-data budget. A single unrepresentable
entity rejects rather than dropping fields. Schema and page decoders reject
duplicate/non-finite/truncated data before a client can publish it to a view.

## Evidence and next implementation

`test_creator_payload.py` verifies Python API behavior. `verify_creator_payload.py`
uses independent malformed fixtures and real C++ stdin/stdout processes.
Debug/Release evidence lives in `out/creator-payload-cross.*.json`.
`creator_payload_cross_language` and `creator_wire_cross_language` are registered
in CTest. The C++ probes compile with C++20 `/W4 /WX`.

`verify_creator_process.py` uses actual interactive processes, synthetic temporary
worlds and explicit restart checks. It covers scoped save/retry/history, handle
admission/release, pinned pages, Unicode workspace paths, malformed input and
unchanged durable bytes after rejected/fatal requests. `test_creator_commands.py`
tests response decoding independently. These do not constitute a finished editor.

The managed Qt client now owns the process, bounds pending queues, rejects
late-generation replies and retains original uncertain transaction bytes.
Next: explicit project metadata/browser, UUID outliner and inspector integration.
No custom engine source has been moved into the separate Unreal demo.
