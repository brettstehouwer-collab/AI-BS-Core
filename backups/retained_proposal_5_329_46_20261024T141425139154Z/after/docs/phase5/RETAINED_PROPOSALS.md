# Reviewed plans to retained proposals - v5.329.46

This is a bounded proposal prerequisite for larger-project support. It does not execute, test or apply generated project code. The disposable Windows worker remains deferred and its acceptance gates remain open.

## Input and ownership

`backend/core/coding_preparation_proposals.py` exposes `review_plan`, `generate_proposal`, `read_proposal`, `recover_proposal` and `cancel_proposal`. Existing preparation-owner authentication is independently required on every operation in `backend/routers/coding_preparation_router.py`.

The parent preparation must be retained and its plan must be `PLAN_PROPOSED` with no outstanding questions. `review_plan` checks the saved inputs and returns `reviewed_plan_sha256`, selected roles/hashes and checks. Generation accepts only that digest and a 32-hex-character proposal ID. The repository, owner, editable files and verification commands cannot be supplied as new authority by the model or this request.

All selected UTF-8 source is included, limited to 20,000 bytes in total and 65,536 bytes of encoded context. Oversized, non-UTF-8, NUL-containing or detected sensitive inputs are rejected. There are no truncated-source full-file replacements. Model responses must describe every selected editable file exactly once, with its original SHA-256 and nonempty, unique, nonoverlapping exact-match hunks. The server reconstructs candidate content from the retained originals and preserves all bytes outside those hunks, including BOM, CRLF and final-newline state.

## Retained evidence and model call

The journal is under the existing owner-hashed preparation:

`saved_data/coding_requests/preparations/<owner-hash>/<request-id>/planning/<plan-id>/proposals/<proposal-id>/`

The input is retained before inference; the result retains the structured output, candidate source, diff, hashes, state and bounded public error information. Complete source and metadata are revalidated, with Windows read handles denying writes/deletion through successful result publication. Independent inspection reconstructs and validates the diff again. These are copies of retained inputs; current project files are not recaptured or promoted.

The provider is the existing `stehouwer_llm:latest` at `127.0.0.1:11434/api/generate`, without environment proxies, redirects, tools or a remote fallback. The client deadline is 90 seconds, provider-response limit 32,768 bytes, context setting 16,384 and prediction limit 4,096. These are limits/settings, not guarantees of latency, token use or model quality. Blocking journal I/O is not a hard OS deadline. One existing coding/planning admission gate is shared.

Terminal states are `PROPOSAL_READY`, `FAILED`, `TIMED_OUT`, `CANCELLED` and `INTERRUPTED`. The same ID inspects retained evidence rather than rerunning generation. Recovery does not replay uncertain work. Authenticated cancellation is independent of the pending POST and is checked again at successful publication. A completed result cannot be replaced by a late cancel. Client cancellation does not prove immediate release of server GPU computation.

Every response states `verification_status: not_run`, `execution_authorized: false` and `apply_authorized: false`. A valid proposal is not a test result, verification seal or permission to apply.

## Routes

Under `/api/chat/coding-tasks/preparations/{request_id}/plans/{plan_id}`:

- `GET /proposal-review`
- `POST /proposals` with `proposal_id` and `reviewed_plan_sha256`
- `GET /proposals/{proposal_id}`
- `POST /proposals/{proposal_id}/recover`
- `POST /proposals/{proposal_id}/cancel`

## Evidence and remaining work

Checkpoint: `backups/retained_proposal_5_329_46_20261024T141425139154Z`.

Retained evidence includes 28 focused proposal cases, 69 preparation/planning regression cases, 13 source-audit observations and 55 actual backend/gateway/model observations. The live fixture reused the earlier selected synthetic Python/JavaScript preparation, generated exact value changes in both files, verified saved content/diffs/hashes, rejected unauthorized and stale requests, preserved originals/checks, inspected/recovered/retried without replay, and cancelled a separate observed-running proposal. No proposed code or selected project checks ran.

The initial service-restoration observer stopped because it expected PID0 for stopped gateway registrations, while this binary reported PID-1. Its original failure is preserved. A later observation verified the same processes, loopback bindings, actual flags, stopped daemon states and health without restarting anything.

Next: show retained proposals and readable diffs in the existing BS-Chat preparation panel, with owner/backend isolation and pending-ID recovery. Frontend proposal controls, expanded isolated execution, coordinated verification/apply, browser acceptance and platform release/signing remain incomplete. This checkpoint completes no additional whole phase.
