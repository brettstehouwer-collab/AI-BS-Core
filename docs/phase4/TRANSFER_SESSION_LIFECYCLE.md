# Durable transfer sessions

Record123 / October26,2026. This implements the file-collection lifecycle in
`isolated_workers/protocol/transfer_session.py`; it is not a task launcher.

## Stored scope and acceptance

`TransferSession` takes a previously authenticated host admission, an exact
manifest, worker/owner/direction, an issued time and an expiry at most30minutes
later. It checks the original manifest contract before initializing its own
dedicated SQLite journal. Scope is stored immutably and must match on reopen.
It requires a separate dedicated `RetainedInbox` for this transfer/direction.
Neither component chooses a host storage path or changes permissions.

The receiver requires the authenticated pinned manifest first, then exactly one
declared opaque part per packet. Part hashes, lengths and path allowlists are
checked before accepted collection progress. Original project names remain
manifest data. The original20files/2MiBperfile/16MiBtotal, Unicode, allowed
dotfiles and immutable verification/dependency rules remain in force.

Every indexed part is cross-checked against the actual retained packet receipt,
packet digest, decoded path and bytes. Stored metadata lengths/types are bounded
before packet/payload allocation. Exact database schemas, durable journals,
synchronous settings and idle dedicated connections are enforced. Unknown
stores and caller-owned transactions are not adopted or rolled back.

The journal stores at most one manifest,40parts and one cancellation. Logical
data bounds do not include SQLite allocation, journal/WAL files or other storage
overhead. Use one inbox per transfer/direction: full input plus full output can
exceed the inbox's32MiB payload quota after wire/base64 overhead. Repeated rejected
or resent packets consume retained quota; no evidence is silently deleted.

## Completion and interruption

States are `WAITING_MANIFEST`, `RECEIVING`, `COMPLETE`, `CANCELLED`, plus derived
`REVIEW_REQUIRED` when unindexed cancellation or unverifiable packet evidence
requires attention. Receipt fields always retain false admission/execution/apply
and verification `not_run`.

`complete(now)` reruns the original whole-file input/artifact validators before
committing `COMPLETE`. Inspection of a completed session and `read_complete()`
also rerun those validators. A stored state label or correct part count alone
does not establish completion. Historical completed bytes can be read after
transfer expiry; they remain data, not fresh execution authority.

The inbox commits authenticated packet bytes and a nonce claim first; the journal
then commits its progress association. **Those two database commits are not one
atomic transaction.** Failed/uncertain acknowledgements can leave retained but
unindexed evidence, or committed progress whose caller saw a failure. Inspect
before any retry. There is no automatic receive/unpack replay or publication.
For an ordinary orphan part/header, a caller may explicitly deliver the same
declared bytes using a fresh authenticated nonce while the transfer is live.

Cancellation requires a codec-authenticated `cancel` message with the exact
transfer ID and manifest SHA256. Accepted cancellation is terminal and preserves
all collected bytes. A retained cancellation whose journal commit failed yields
`REVIEW_REQUIRED`, blocking receive/completion. Explicit
`recover_cancellation(nonce, expected_digest)` verifies that existing evidence
and commits terminal collection state without receiving/claiming it again.
Malformed evidence remains blocked; valid foreign-owner evidence cannot cancel
this transfer.

Cancellation here stops **file collection**. It does not cancel a process, VM or
running job. Outbound acknowledgements, file materialization/publication, worker
leases and task cancellation remain separate integration work. All session
writers must use the same journal and exclusively own their dedicated inbox;
direct concurrent inbox writers violate the caller contract.

## Deployment boundary

This implementation uses the existing **HMAC envelope path**, not the live
mTLS-only guest diagnostic channel. No production endpoint, new host/guest key,
execution grant or18443operation is added. The signed-in integration guest and
existing staged Number Summary fixture are unchanged.

Both stores need a protected host-owned registry, validated caller, owner/DACL,
ancestor and handle identities, trusted runtime/source dependencies and a real
exclusive broker lifecycle before deployment. The existing metadata-only root
review and `ExchangeFiles.Describe/Open` do not establish those prerequisites.
The read-only review also found inherited-leaf and OWNER RIGHTS template cases
that the future native policy must reconcile explicitly.

Actual guest delivery, separate licensed execution-image admission, fourteen
containment cases, host-issued job dispatch and process cancellation, Phase5/6
acceptance and separate host apply remain open.

Evidence and actual terminal test output are retained in
`backups/transfer_lifecycle_20261026_record123/`. These tests use real disposable
SQLite files and synthetic packet bytes; they never execute collected project
contents or replace actual VM acceptance.
