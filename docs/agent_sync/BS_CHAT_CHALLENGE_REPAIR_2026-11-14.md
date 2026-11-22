# BS-Chat challenge repair — November 14, 2026

Scope: context-budget rejection, model404 and opaque local transport failures reported in the supplied challenge transcript. Current user request authorizes scoped repair and live local inference verification, not model replacement, installation or unrelated activation.

## Implemented

- Implicit source retrieval is a whole optional context block. Explicit attached-source evidence retains mandatory admission and is never silently truncated.
- An optional specialist proposal is omitted with a visible notice if it cannot fit beside the full current request and required context. Incomplete specialist output is not used as primary context.
- Specialist history admission uses the actual chat/generate representation and required source size. Its bounded request timeout now matches the180second primary limit rather than the former90second limit.
- Transport classifies read/write/pool timeout, read/write interruption and protocol errors. Bounded404inspection distinguishes exact-model absence and known missing API routes without exposing provider error bodies. No post-response generation replay, model switching or paid fallback was added.

## Verification

Recovery Python ran59focused offline checks successfully. Added cases cover oversized implicit retrieval, oversized optional proposals, incomplete specialist output, classified404/timeouts, partial-output preservation, no replay and lease cleanup. Full source copies and focused log retained in `backups/chat_challenge_repair_20261114_v01`.

Both live Ollama catalogues and /api/show currently recognize the exact requested models. This does not prove the cause of the historical404; old model-store/server state remains unproven. The91.277second historical failure is consistent with the old90second specialist read timeout, not definitive traceback evidence.

The guarded runtime restart saved8validated private SQLite snapshots, then failed because the OS-reported base Python executable lacks uvicorn. Failed evidence remains in restart-result.json and api.stderr.local.log. Existing reviewed recovery launcher restored the API with prior held activation settings. Health200, authenticated admission200 and anonymous403 passed. No exact old-runtime rollback or complete logical database equality is claimed by this checkpoint.

One fresh authenticated POST to `/api/v1/hybrid-chat/stream` used the original supplied challenge, empty synthetic history and selected `stehouwer_llm`. Specialist and primary both reported clean completion. HTTP200;101.34seconds; no inference error codes. Primary input4931UTF8bytes within its6656byte admission limit. The proposal was omitted because it did not fit. Receipt: `backups/chat_challenge_repair_20261114_v01/live-result.json`. Raw response is restricted to that checkpoint's private subdirectory; do not upload it as public engineering evidence.

## Remaining limits and next step

Transport completion is VERIFIED; answer correctness FAILED. The primary answered12minutes, scheduling E at7although D ends9. Correct optimum is14minutes. No second model request, model substitution, claimed memory-retention success or automatic corrective replay followed. Future reasoning-quality work should use dependency validation and bounded synthetic benchmarks as a separate selected scope.

Source remains146; retained installed/native artifacts and hosted build are not qualified by this backend-only change. The existing creative launcher source pins may now be stale due to the dispatcher change and must be reconciled and requalified before creative use. This checkpoint is local; no new Drive backup or restore verification is claimed.

## Later source/status reconciliation — November 14, 2026

The preceding paragraphs retain the original repair receipt and its limits. The later Coding mode v01 checkpoint records all 16 creative executable/dependency pins matching at its scoped source check. That comparison supersedes the earlier possible-stale-pin warning for those checked bytes; it does not establish the full live creative contract, a mounted writer workflow, installed parity or release acceptance. Use the latest pinned-source receipt before subsequent creative work.

The subsequently pasted chat transcript contains the same generic provider404, context-budget and transport failure classes but no embedded event timestamps. Its attachment write time is not the failure time. Read-only comparison cannot classify each displayed event as an old failure or a fresh recurrence. Current source contains the repaired optional-context admission and specialist180second timeout, while this receipt proves one fresh clean transport completion. Neither source presence nor that one pass proves every displayed failure resolved. Reasoning correctness remains FAILED for the recorded answer; no replay or replacement model was requested by this reconciliation.

Coding mode is now implemented in backend/native/browser source. Retained execution discovery, static Python/JavaScript/JSX validation, scoped proposal/planning regressions and trusted-local synthetic process checks have separate receipts. The user authorized trusted local checks only through an explicit per-task choice and acknowledgement of local-account file/network access; isolated mode stays default and never falls back silently. These coding checks do not qualify ordinary chat reasoning or overwrite this challenge result. Current source progress belongs to `docs/architecture/BS_CHAT_CODING_MODE_2026-11-14.md` and the next session-close checkpoint `backups/bs_chat_coding_mode_20261114_v02/checkpoint.json`, pending until written. No production Coding activation, model request, service change, private transcript export or new Drive verification follows from this note.


Final scoped checkpoint: `backups/bs_chat_coding_mode_20261114_v02/checkpoint.json` is written. The single integrated synthetic gate passed156/156 with all frozen code hashes unchanged. This supersedes earlier pending-pointer text; it does not establish mounted/live acceptance or production activation.
