# Local checkpoint format 1 — SDK 0.2.0

This is an interim standalone Windows PC checkpoint adapter for the custom engine. The existing plan's SQLite-backed LocalSaveStore and MasterDbSaveStore remain future adapters. This implementation does not open or migrate `backend/aibs_master.db`.

## Envelope and payload

All integer fields use explicit little-endian encoding. Header: 8-byte `AIBSSAVE` magic, u32 format version (1), u64 payload length, u32 CRC32 of payload. CRC32 detects accidental corruption; it is not authentication. Double values are stored as IEEE-754 binary64 bits. Strings are length-prefixed byte sequences, not OS paths. The file rejects extra/truncated bytes and unsupported versions.

The payload stores project/branch identity, world UUID, checkpoint UUID, revision, numeric field schemas, all allocated/retired entity UUIDs, current world, Adam events, accepted operation receipts, and undo/redo before/after worlds. No pointers, runtime handles, model context or derived renderer/physics resources are serialized.

Each event has its project, branch, world UUID, sequence revision, operation, kind, realized UUID-bearing edits and description. Each receipt retains the original request separately from realized edits; an empty requested Create UUID remains an exact retry match after restart. A reused alias cannot change the meaning of an old event. History is replayed and compared against saved history/world before load publication. Even transient Create-then-Erase effects validate individually.

Limits: 16 MiB total file; 4,096-byte strings; 10,000 entries per collection; 200,000 expanded entity/field units; 200,000 replay work units and 64 MiB estimated copy work. These are initial small-scene budgets, not production world capacity or a strict process heap limit. Both save and load enforce bounded serialization. Schema changes require an explicit future migration; format 1 currently rejects mismatches.

## Publication and restart

The caller chooses a path in an existing directory. A sibling exclusive lock serializes cooperating readers/writers. Saving to an existing slot compares its world identity and checkpoint head with the owning session, rejecting stale/wrong-world saves.

Save prepares one immutable snapshot, validates it, writes a UUID-named temporary file in the same directory, flushes and closes it, then replaces the checkpoint path. Only successful publication updates the live checkpoint head. A failed save does not claim durability or clear outstanding world changes. Load ignores temporary files, fully stages/parses/validates a candidate, and swaps validated state into the session without allocating during publication.

The Windows adapter uses [FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers) and same-directory [MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw) replacement with write-through requested. The exercised filesystem is local C: NTFS. Forced process-exit tests establish recovery at the observed publication boundaries; they do not establish immunity to hardware power loss, failing disks, arbitrary network shares or noncooperating external writers.

Pre-publication process exits can leave UUID-named temporary files. Loading safely ignores them. Generated-storage telemetry counts those bytes; automatic orphan cleanup/retention is future work. Lock files are persistent empty coordination files. No user checkpoints are automatically deleted.

## Verified scenarios

- Separate writer and reader processes preserve the exact world/entity IDs, field values and Adam event count.
- Forced exit after the temporary file is flushed and before publication leaves the complete previous checkpoint.
- Forced exit immediately after publication leaves the complete new world and memory.
- Restart preserves accepted-command deduplication, undo/redo, deleted/recreated identities and schema/scope boundaries.
- Corrupt/truncated/future-version/extra-byte files fail without changing live world, memory or checkpoint head.
- Checksummed non-finite fields, wrong scope, over-limit counts and invalid transient memory creations are rejected.
- Another world or stale loaded session cannot overwrite a newer slot head.

Older saves may be explicitly loaded within their declared branch; automatic branch creation, archived alternate futures and cloud/device synchronization are not implemented. There is no autosave timer or phone writer. The planned Adam companion receives PC-authoritative progression; pairing, transport and cross-device command delivery remain future work.
