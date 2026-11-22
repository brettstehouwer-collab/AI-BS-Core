# Native Chroma investigation and verification — Record200 / ADR-124

Source **v5.329.78**. Updated 2026-10-31T07:47:42Z. Whole-system audit and verification remain **PARTIAL / IN_PROGRESS**. Live trading remains disabled. Firebase continues to serve the verified v5.329.77 release; v78 is the new source/build checkpoint.

## Native Chroma diagnosis

A fresh complete disposable clone isolated the access violation to collection f5b03192-d10f-4b91-bef0-36b1b1a6ccbe, vector segment 2e1c203a-a4ae-42c8-995e-7703aea48a4d. Chroma1.5.9 exits with Windows0xC0000005 during count(), before document retrieval/filtering. The other previously untested empty collection passes. No model or Chroma service was activated.

The index contains **1,169 duplicate active external labels**, with no deleted flags. Its upper-link file is malformed at byte18,524: a declared7,340-byte record violates the68-byte level alignment and the204-byte maximum implied by header level3. All other populated segment graphs passed those checked invariants. The file-format reference is [upstream HNSW persistence source](https://github.com/chroma-core/hnswlib/blob/master/hnswlib/hnswalg.h).

The current mapping has1,169 missing and1,169 ambiguous identity/vector associations. The267 queued vector facts do not supply authoritative replacements for those identities. Suppressing replay makes metadata reads pass on deliberately inconsistent diagnostic copies; **those copies are not repairs and were not promoted**. Complete identity-faithful reconstruction remains unverified and requires authoritative recovery evidence. No graph, queue, collection or original data was deleted, replaced or silently regenerated.

The earlier FTS repairs remain valid. FTS integrity does not establish HNSW integrity. A preliminary interpretation of length.bin as integer link lengths was rejected: that file stores float normalization data; upper-link lengths are inside link_lists.bin. All164 root-store files and all5 local-store files retain their recorded hashes.

## Applied fixes and next phase

Added a filesystem-only diagnostic in backend/core/chroma_native_integrity.py and scripts/inspect_chroma_store.py. It uses bounded binary reads, rejects reparse points, checks file/directory changes, and reports unsupported or changing observations as unverified. It imports no Chroma/native client, opens no SQLite database, executes no pickle and makes no health or recovery guarantee. The confirmed corrupt segment is reported without invoking the crashing reader. This is a diagnostic, not a universal wrapper around all legacy Chroma callers.

The expanded suite exposed a disabled RecDebut review hold. The source hard hold is restored so activation environment flags cannot release reviewed outreach. All59 workflow and49 TextBee cases passed offline. Two stale fixtures were corrected without weakening production behavior: conversation memory now links the actual chat-auth module to an inert Firebase user; personal-memory tests load the actual private-header constant. Existing assertions are retained.

The subsequent registry phase fixes the1,000-row catalog ceiling and late plugin conflict omissions. Default/max response pages remain1,000; global visits remain bounded at10,000 and depth8. Global indexes, cross-page duplicate references and metadata snapshots support stable paging; stale snapshots return409. Administrator admission precedes query validation. Route order, existing handler behavior, lifecycle holds and private/no-store headers are preserved. The15 registration cases and76 related cases pass. No duplicate handler was silently deleted.

The restarted loopback backend now exposes all **2300 observed route records** in one stable bounded snapshot, including **943 duplicate registration records**. The larger duplicate count reflects previously hidden catalog coverage; it is not a count of independently proven exploits. Metadata enumeration invokes no registered business handler. Duplicate ownership, module-body import effects and the missing chef analytics dependency remain open.

## Full verification result

Inventoried121 canonical test files:99Python and22Node. The accepted set passes **1378 Python cases across88files plus 226 Node cases across22files**, total **1604**, with zero accepted failures, skips or guard denials. Eleven Python integration files remain held;114 attempted cases are excluded, and setup blocking means this is not their complete declared case count. Overall status is **PARTIAL**, not an all-system pass.

The canonical four-job batch passes 191 Python and75client tests, strict TypeScript and all16version paths. These overlap the expanded totals. The isolated production build passes5,678modules and143compiled outputs.337retained E: SQLite fixtures pass read-only integrity checks with bytes unchanged; intentionally corrupt rejection fixtures and an earlier row-factory comparison bug are accounted separately.

Held integration groups cover guest/VM execution, cold/native startup, configured-directory/database initialization, helper subprocesses, native filesystem/DACL boundaries, optional audio, and provider certificate/network lookup. Full per-file status and exact commands are in VERIFICATION_v5.329.78.json and restricted evidence/verification200/final_matrix_v78.json. The accepted replay command is documented there; it never retries the11held groups.

## Isolation incidents and limits

Two earlier native fixture attempts bypassed the Python write audit hook and created10empty UUID test directories at C: root. Their task ownership, creation windows, non-reparse state and emptiness were checked; each was removed with nonrecursive rmdir. Existing data removal was not observed. No OS-wide ACL proof is claimed. A failed FE Express fixture may have read the exact local-service credential profile through native Windows APIs; no value was printed or network sent. The corrected accepted run uses explicit inert credentials. Python hooks are effect screening, **not an OS sandbox**.

Git fixture path-length failures were fixed by shortening owned E: paths; no global Git setting changed. SQLite inspection receipts now normalize row values; raw false negatives and expected rejection errors remain in evidence. These are disclosed harness corrections, not hidden product passes.

## Runtime, data and history

The backend was identity-checked, stopped, and its current master/trading/cache records and adjacent SQLite journals preserved in an authenticated11-file archive before restart. Fresh startup retains seven false background/outreach flags, payment mode disabled and DRY_RUN/HOLD_DISPATCH. All14 read-only admission probes pass; route paging separately verifies403/422/409 behavior. Crypto8007 remains absent, and the four protected execution/monetary hashes remain unchanged. No trade, payment, outreach or workload was dispatched by verification.

Nine existing ledger prefixes are retained byte-for-byte before appending Record200. Exact source preimages, patch manifests, test outcomes and recovery receipts are kept in the restricted campaign and uploaded only into the established [single Drive folder](https://drive.google.com/drive/folders/1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k). Recovery keys remain outside repository and cloud. Package download/decrypt/restore outcomes are recorded separately after upload; no unverified cloud outcome is implied by this source checkpoint.

ADR-124: preserve authoritative data and pending facts; distinguish static checks from native readiness, and qualified verification from a full pass; page bounded metadata without changing dispatch behavior. Next work: obtain authoritative missing/ambiguous vector evidence, review duplicate ownership/import effects, and isolate the held native/provider integration tests before execution.
