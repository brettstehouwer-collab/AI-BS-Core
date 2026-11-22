# Crypto subsystem integrity audit — 2026-10-30

Static review and offline source remediation in `C:\AI-BS`. **The inspected live execution paths are not ready for live trading.** Source changes now reject order dispatch pending reconciliation. Existing processes, compiled binaries, exchange orders and account balances were not inspected or controlled by this audit.

No live orders, cancellations, private exchange probes, service restarts, deployment, credential changes or production-ledger repairs were performed. Public documentation retrieval was the only intentional external service access. Original monetary records were preserved.

## Critical / high risks

References in this table describe the **before snapshot**, retained under `C:\AI-BS\backups\crypto_integrity_audit_20261030T184032Z\before`. The exact patch and manifests in that checkpoint distinguish original defects from containment changes.

| ID | Severity | Finding and consequence | Source evidence | Result of this audit |
|---|---|---|---|---|
| C1 | Critical | Eight direct Python order calls update local holdings using requested quantity and quoted price, without consuming confirmed fills, actual fees or final order state. A timeout can be followed by another autonomous order even if the first was accepted. Go treats failed live requests as simulated completed orders. This permits duplicate exposure and fictional balances. | `backend/crypto_trader_bot.py` order sites and TWAP loop; both `internal/daemons/trade_engine.go` completion branches | **Contained in source:** centralized closed Python protocol, Go guards at both order/client-request layers, and removal of error-to-paper completion. Fill reconciliation and durable intent recovery remain unimplemented. |
| C2 | Critical | No shared enforced maximum notional, aggregate exposure, daily budget, or consecutive-rejection circuit breaker. Minimum-size clamps are not maximum limits. Hard stop-loss is missing in the Python scalp path; its trailing exit arms only after profit. Go watchers remove tracked positions when queuing an exit, before a sell is confirmed. | Python strategy/evaluation/settings functions; both Go `watcher.go:200–221`; Go allocation-based execution | **Contained in source:** all inspected dispatch held; autonomous Python order workers not started; Go watchers and Diamond Hand return before changing tracking. This does not establish protective stops or close existing exposure. A configurable live rejection-threshold breaker remains future work. |
| C3 | Critical | Canonical execution records can be synthetic: executive limit orders insert `EXECUTED` with a fabricated transaction identifier; mobile force-swap rewrites holdings without exchange execution; the drip simulator writes `tx_sim_*` executions into the shared queue. One such simulated `EXECUTED` row is actually present. | `backend/core/executive_action_dispatcher.py:940–1000`; `backend/commercial_gateway/crypto_control_router.py:120–165`; `Crypto-Swarm/drip_trader_daemon.py:90–172` | **Future contamination blocked:** fake executive/swap success paths rejected, paper storage isolated and marked `PAPER_FILLED`. Historical rows retained and explicitly unverified; no invented correction/migration. |
| H1 | High | `Crypto-Swarm/drip_ledger.json` is **811 NUL bytes**, not JSON. Python loader previously turned missing/corrupt monetary state into cached/empty holdings; saving advanced the cache before persistence and swallowed failures. Go Diamond Hand also defaults corrupt JSON to empty positions and ignores overwrite errors. | JSON byte probe; Python `load_ledger` / `save_ledger`; Go `diamond_hand.go:29–57` | **Partly repaired:** strict Python reads, finite-value checks, unique same-directory temporary files, flush/fsync and atomic replacement; failures propagate and cache changes only after persistence. Go strategy held before reads/writes. Corrupt original retained; no recovery source has been established. |
| H2 | High | Order acknowledgement is treated as execution; partial fills, fee currency, cancellation/remainder and unknown outcomes are not represented. Go HTTP handling does not explicitly reject 429/503 before decoding; absent API code can be read as success. Generic fixed retries do not distinguish rate limits, rejected orders and ambiguous timeouts. | Both Go clients' `doRequest` / `CreateOrder`; Python order call sites and workers | **Contained, not implemented:** no live order is attempted through the reviewed guarded paths. Before reopening, classify provider errors and reconcile unknown order outcomes rather than resubmitting them. |
| H3 | High | Mutation endpoints lack meaningful authentication and finite upper risk bounds. Wildcard CORS expands browser access. The executive emergency flag was local-only and resume did not coordinate workers. | Daemon POST decorators/CORS; gateway settings; executive pause/resume | **Reduced:** daemon and gateway mutations return 503; allowed browser origins narrowed; source status is held, resume rejected. Operator pause persists a halt marker and propagates persistence errors. Current guards are unconditional: deleting/changing the marker cannot enable trading. Endpoint authentication and a coordinated live control plane still need implementation. |
| H4 | High | Crypto.com custom signing uses HMAC-SHA256, but request ID increment is unsynchronized and millisecond wall-clock nonce has no clock-drift/concurrency handling. Flat parameter signing follows the documented concatenation; nested values use Go formatting rather than recursive exchange canonicalization. Legacy v2 endpoint compatibility is unverified. A hardcoded internal intent secret exists and intent validation is bypassed. | Both Go `buildParamString`, `sign`, `doRequest`, execution loop; local installed CCXT Crypto.com signer | **Contained:** guarded create requests cannot reach signing/network. No actual exchange-key disclosure was established. Replace internal secret/configuration and restore intent validation; use tested canonicalization and official signing vectors before live use. |
| H5 | High | Encrypted credential-decryption failure previously passed the ciphertext back as a candidate key. Exchange errors are sometimes logged verbatim and may contain request context. | Daemon `decrypt_vault_key` and worker error logging | **Reduced:** decryption now returns no key on failure; watcher logs exception class without raw provider payload. A complete historical log/secret scan was not performed, and no claim of credential compromise is made. |

## Medium / low risks

| ID | Severity | Evidence and impact | Remediation / residual |
|---|---|---|---|
| M1 | Medium | Money uses Python/Go binary floats and SQLite `REAL`. Estimated fee deduction and clamping negative realized P&L to zero can materially misstate returns. CRO trade schema lacks exchange order/fill identity, fee currency, and live/paper provenance; P&L defaults are not populated by its logger. | Unresolved economic accounting. JSON validation rejects non-finite/negative position values, including oversized integers, but is not reconciliation or decimal accounting. Use decimal strings/scaled integers, exchange precision/minimum rules, and fee-aware fill records. |
| M2 | Medium | Two SQLite trade sources diverge: seven legacy versus six master rows. Router selected master solely because the file exists. `coin_amount * coin_price` differs from `usd_value` by more than 1e-6 in six of seven legacy rows and all six master rows. | Read APIs now identify historical/unverified state and source and do not turn DB errors into an empty successful ledger. No silent merge. Missing fee/valuation semantics prevent attributing the arithmetic differences to an error. |
| M3 | Medium | Serial WebSocket sends can block strategy evaluation; quiet WebSocket fallback synthesized order-book depth from ticker data. Reconnect waits were fixed and uncapped in retry count. | Concurrent sends now have one-second per-client deadlines; fallback requests real depth with a ten-second bound; market-data reconnect delay doubles with jitter to a bounded maximum. Recovery attempts remain unlimited; outer worker restarts still need a restart budget. |
| M4 | Medium | Watchdog polled private-balance-dependent telemetry with a three-second deadline and killed/restarted after three failures. Multiple supervisors/restarts and Go public `http.Get` calls lack comprehensive bounds. | Watchdog now uses local `/healthz`, which does not touch ledger/exchange. CCXT request timeout is ten seconds. Full supervisor ownership/restart budgets and all Go public HTTP deadlines remain unresolved. |
| M5 | Medium | Both Go API servers listened on all interfaces (`:8001`) although logs described loopback. Daemon telemetry advertised synthetic balance/performance; other routes claimed enforced limits/online state without checking them. | Both Go servers now explicitly bind `127.0.0.1:8001`. Synthetic cash/performance removed from daemon telemetry. Reviewed control/trading APIs report held/unverified; false liquidation-success endpoint returns 503. Binding is source-verified only. |
| L1 | Low | Generic 429/503 retry spacing and separate exchange clients can compete for per-account budgets. | Before live reactivation, share request budgets, honor `Retry-After` where supplied, use bounded jitter, and reserve capacity for reconciliation/protective operations. A create-order timeout or 503 is potentially ambiguous and must not be blindly retried. |

## Daemon and network result

**VERIFIED, source:** the scalp daemon entry point binds `127.0.0.1:8007` in [crypto_trader_bot.py](C:/AI-BS/backend/crypto_trader_bot.py:1269). Port 8001 belongs to the separate Go API, whose two copies were corrected to loopback. No current listener/PID, native browser session, exchange connection, or deployed binary was exercised; runtime binding remains **UNVERIFIED**.

The before code did not contain a shared `execute_trade_protocol` implementation. All eight Python exchange order sites now route through [the new protocol](C:/AI-BS/backend/core/crypto_execution_safety.py:44), which rejects before touching an exchange. Credential presence, missing/corrupt halt state, and API resume cannot open it. The source deliberately has no live-enable switch. Shutdown now awaits cancelled tasks before closing the exchange client.

This containment also stops source-level automatic exits. It is **not an emergency liquidation system** and does not cancel exchange-held orders, manage existing exposure, or alter a running old process.

## Ledger integrity evidence

Probes used stdlib SQLite read-only URIs and direct byte reads, without importing application database initializers. Machine-readable evidence: [integrity_evidence.json](C:/AI-BS/backups/crypto_integrity_audit_20261030T184032Z/integrity_evidence.json).

| Store | Observed result |
|---|---|
| `Crypto-Swarm/drip_ledger.json` | Invalid JSON; 811 bytes, all NUL. SHA-256 `6a31b6bcf6fd89ef35ff6e7c41ba9749f559edcb97e5900649ddd291b12db098`. No active writer for this file was established in the reviewed paths. |
| `Crypto-Swarm/trade_queue.db` | `quick_check=ok`; one TWAP plan, 25 drip orders; one simulated row marked `EXECUTED`. Plan arithmetic `total = executed + remaining` passes within 1e-8. |
| `backend/drip_ledger.db` | `quick_check=ok`; seven trades and one ledger-state row. |
| `backend/aibs_master.db` | Six trade rows exactly match six legacy rows across common columns; one legacy-only row. Whole master database integrity check not run. |
| `database/cro_quantitative_ledger.db` | `quick_check=ok`; 45 trade records: BUY 8, DCA_IN 26, LIMIT_ORDER 3, SELL 2, TAKE_PROFIT 6; one price record, zero macro events. Limit placement must not be counted as a confirmed fill. |

`quick_check` establishes SQLite structure, not legitimate execution. None of these observations establishes a reconciled account balance. No authenticated exchange fill/fee statements were fetched. Both JSON ledgers' hashes match the initial audit manifest after testing; database records were not repaired, relabeled or deleted.

The relaxed Zero-Mock development rule allows ephemeral fixtures but prohibits fake balances/transactions in production stores. The paper daemon now requires a new database under OS temporary storage outside the repository, refuses canonical retargeting/hardlinks, labels synthetic fills `PAPER_FILLED`, and defaults to no-write standby. `--status` opens the old queue read-only. Existing `backend/test_twap_queue_resilience.py` was **not run**: its mocked successful order path can call the real ledger saver and import a module with schema initialization side effects.

## Applied code and verification

Primary updates:

- [Closed execution protocol and durable halt](C:/AI-BS/backend/core/crypto_execution_safety.py), [strict ledger I/O](C:/AI-BS/backend/core/crypto_ledger_io.py), and eight daemon order-site integrations.
- Both Go client/order guards, removal of live-error-to-paper completion, watcher/Diamond preservation holds, and loopback API binding.
- Kraken dispatch hold, rejected executive fake fills/resume, rejected liquidation script/API, and truthful gateway/trading responses.
- Isolated paper storage; local liveness endpoint, bounded market-data I/O and subscriber sends, backoff, and awaited shutdown.

Final offline checks:

| Command / scope | Actual result |
|---|---|
| `python -X utf8 -m unittest discover -s scripts/tests -p test_crypto_integrity_containment.py -v` | **13 passed**, 0.126s. No daemon imports, real database fixture writes, or private exchange calls. |
| `go test -v ./internal/daemons ./internal/api` in `Crypto-Swarm`, with `GOTOOLCHAIN=local`, `GOPROXY=off` | **4 passed**; API package compiled with no tests. |
| Same command in `Crypto-Swarm/cryptoswarm-desktop` | **3 passed**; API package compiled with no tests. |
| AST syntax parsing of changed Python source/tests | **12 files passed**, no application imports. |

Checks cover zero exchange access during hold, failed ledger replacement preserving original bytes, corrupt/missing/non-finite state rejection, durable halt failure propagation, isolated paper execution/canonical retarget rejection, mutation routes rejecting before credentials/body access, both Go dispatch layers, and Go watchers stopping before tracking changes. They do not validate live fills, market behavior, profit, authentication or exchange protective orders.

Initial test failures were retained: Windows temporary database connection cleanup, then distinct default-encoding errors in two AST test reads. Explicit connection closing and UTF-8 fixed them. A read-only evidence probe initially assumed `amount`/`price`; actual legacy columns are `coin_amount`/`coin_price`, corrected after schema inspection. No same failing diagnostic was repeated twice without a pivot.

## Remaining work before any live reactivation

1. Select an authoritative account ledger; obtain exchange order/fill/fee/balance statements and reconcile all ambiguous and historical records without overwriting originals. Establish live/paper provenance and immutable unique fill identities.
2. Implement a durable order state machine: intent/client identifier, submission, unknown, acknowledged, partial, filled, cancelled/rejected. Recover ambiguous outcomes by lookup before considering another dispatch.
3. Apply shared decimal-aware order/position/day limits and fresh executable-depth slippage limits at the final dispatch boundary. Validate minimum notional, amount step and price tick independently. Reject non-finite/negative values.
4. Implement confirmed-fill-based stops/trailing exits, partial-fill remainder handling, and a shared durable rejection breaker requiring deliberate recovery. Do not remove tracking until confirmed exit fills are accounted for.
5. Restore authentication/intent validation; test signing vectors, clock behavior, HTTP/API rejection and rate budgets; bound supervisors and public HTTP calls. Complete a separate controlled loaded-runtime review before claiming any activation.

No restart or activation follows from this report. Existing unrelated working-tree edits, model/document archives and personal databases remain outside this change.

## Primary references

Crypto.com documents HMAC-SHA256 signing, the request/nonce inputs and HTTP 429/API 42901 rate limits in its [REST common API reference](https://exchange-developer.crypto.com/exchange/v1/docs/api/rest-common-api-reference). The custom Go flat-parameter signature was compared to that construction; nested canonicalization and the legacy endpoint remain unverified.

The [CCXT Manual](https://github.com/ccxt/ccxt/wiki/Manual) explains that create-order timeouts can leave execution unknown, that order lookup/balance checks are needed before recovery, that precision and limits are different, and that rate limiting belongs to each exchange instance. Local installed CCXT version was 4.5.70. These references support the recovery requirements; they are not evidence of this account's execution history.
