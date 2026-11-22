# Scoped integration data protocol v1

This dormant codec accepts explicit bytes, not host paths. It implements an
HMAC-SHA256 envelope bound to worker, owner, direction, immutable base hash,
nonce and a maximum five-minute validity period. A manifest binds each approved
relative path to its exact size and SHA-256. Inputs can require immutable hashes;
outputs remain data for review. Packet, file-count, individual-file and aggregate
byte limits are enforced before acceptance. Windows aliases, traversal, streams,
device names, duplicate/case-colliding paths and unapproved paths are rejected.

`pack` serializes supplied bytes; `unpack` authenticates and validates them before
calling the replay claim adapter. Neither function reads, materializes, executes
or applies a host file. Returned bundles carry execution/apply authorization false
and verification status `not_run`. Authenticated cancel/ack messages are data;
their acceptance does not prove an operation was cancelled or acknowledged.

`ReplayClaims` uses a caller-provisioned dedicated SQLite connection. Creation
refuses nonempty schemas, reopening and claims check the exact schema, and nonce
uniqueness is committed before the codec returns accepted bytes. It stores only
scope, nonce, digest and expiry, never packet payloads or authentication keys.
The store must be persistent, with a durable journal and FULL/EXTRA synchronous
mode; these settings are checked at construction and before each claim. One
connection must be serialized or exclusively owned by one request thread. Control
messages retain their job scope but do not require attaching the job's inputs.
No pruning occurs. Receiver crashes after claiming can still leave delivery
incomplete: durable incoming-packet retention, receipts, inspect/recovery and
interruption-safe artifact publication remain integration work.

No service, route, scheduler or VM entry imports this codec. Deployment must
provision private per-worker keys and storage through the real standard worker,
provide confidential authenticated transport, pin identities and source, and
implement safe handle-based filesystem access and denied-host-access tests.
HMAC provides integrity/authentication, not encryption. Do not use an application
developer key or send private-store/model bytes. Type/path exclusions are defense
in depth; the sender must approve the actual selected data.

Tests exercise codec behavior, real disposable SQLite restart/concurrency and
negative cases. They do not establish guest connectivity, entitlement, TLS, safe
Windows materialization, cancellation/recovery, transport or containment acceptance.
Disposable SQLite fixtures are preserved under the Record111 evidence directory.

    python -m unittest discover -s C:\AI-BS\isolated_workers\protocol -p "test_*.py" -v

## Record123: durable collection lifecycle

`TransferSession` now joins a dedicated retained packet inbox to an exact-scope
transfer journal, with manifest-first collection, whole-file completion checks,
terminal collection cancellation and explicit interrupted-cancel recovery.
Cross-store commits remain non-atomic and recovery never replays receive/unpack.
The HMAC path is not the live mTLS-only guest channel; production broker/root,
file publication, task-process cancellation and VM acceptance remain open.
See `docs/phase4/TRANSFER_SESSION_LIFECYCLE.md` and Record123 test evidence.
