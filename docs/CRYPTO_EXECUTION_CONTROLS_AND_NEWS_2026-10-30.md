# Crypto execution controls and advisory news — Record188

**Status: VERIFIED offline implementation; live execution remains unconditionally held.**

The requested fill accounting, durable order recovery, shared risk policy and stop controls are implemented in an isolated coordinator. The supplied RSS/Ollama request is implemented as a separate, dormant advisory pipeline with a read-only API and dashboard panel. No worker, service or model was started; no exchange or news endpoint was contacted by the tests. Version remains v5.329.72.

## Critical / High risks

| Finding | Remediation applied | Remaining boundary |
| --- | --- | --- |
| Requested order quantities were treated as completed trades; partial fills and fees were not authoritative. | `backend/core/crypto_execution_controls.py` applies immutable, deduplicated fill receipts to inventory, quote cash, cost basis and realized PnL in one transaction. An acknowledgement changes no balance. | This is an offline coordinator. Legacy callers remain blocked and must be replaced before any live integration. No real balance or profit is certified. |
| A timeout or restart could repeat an accepted order or release its reservation. | Durable intent precedes submission; `SUBMITTING`/`UNKNOWN` retain reserves across restart. Timeout, connection loss and HTTP429/503 require lookup. No expiry or automatic resend exists. Terminal reconciliation requires exact applied cumulative fills. | A trusted exchange adapter, authoritative order/fill lookup and recovery of existing exposure remain unimplemented. |
| Independent workers could exceed account limits or oversell shared inventory. | `BEGIN IMMEDIATE` checks and reserves atomically using persisted immutable policy. Limits cover order, position, aggregate exposure, daily turnover, open orders, slippage, fee allowance, quote age and drawdown. Pending buys include worst-case fees; unfilled sells do not reduce exposure. Submission rechecks limits and quotes. | All workers for an account must ultimately use one coordinator. No live caller is connected to it. |
| Consecutive rejected orders could run indefinitely. | Durable rejection threshold, submission generations and hard hold survive restart. Duplicate responses and old-order successes cannot reset newer rejections. Unknown submissions block new dispatch decisions. | No reset/live-enable API was added. The existing unconditional source hold remains intact. |
| Trailing stops could forget peaks, trigger repeatedly or assume an exit filled. | Stops arm from actual gross fill price. Every accepted quote persists the high-water mark, effective threshold and trigger latch. Thresholds never loosen; rebound/restart cannot erase a crossing. Stop evaluation reserves one exit generation atomically with discretionary sells. Partial/cancelled exits retain protection for remaining inventory. | No live stop order is sent. Limit exits cannot guarantee a fill; current source holds do not liquidate existing exposure. Conservative fee reserves can leave dust. |
| News could turn into unvalidated trades, cloud inference or fictional neutral results. | News has a separate database and no order/strategy/SHM imports. Fixed public feed destinations, literal loopback Ollama, explicit `model:tag:local`, local GGUF metadata checks, strict structured output and ticker allowlist. Failures have explicit retry/unavailable states. | Worker remains dormant. Local server compatibility, model availability, feed health and signal quality have not been measured. |
| Corrupt/divergent historical ledgers could be silently reconstructed. | Existing monetary files are preserved; fixtures require tagged new OS-temporary stores outside the checkout. Unsupported fee facts remain pending with a durable hold. | The earlier audit's 811-byte NUL drip JSON, simulated historical queue entry and divergent SQLite histories remain unresolved. No financial history was repaired. |

The original daemon/network/signing findings and source containment remain in [Record187](CRYPTO_SUBSYSTEM_INTEGRITY_AUDIT_2026-10-30.md). Source binds remain unchanged by this task: daemon `127.0.0.1:8007`, duplicated Go API `127.0.0.1:8001`. Existing loaded processes and exchange-held orders were not inspected or modified. A source hold is not evidence of a stopped old binary or an active protective exit.

## Execution implementation

The coordinator has no default production database, exchange client, network implementation, worker registration or live activation switch. It only creates explicit new OS-temporary `OFFLINE_ONLY` databases and reopens matching stores. Legacy `execute_trade_protocol` continues to reject before exchange I/O.

Financial amounts are Decimal values stored as SQLite TEXT, with bounded inputs and a 96-digit arithmetic context. Binary floats, booleans, NaN, infinity and excessive precision are rejected. Quotes and quantities obey instrument ticks, steps and minimums. Quote fees reduce cash, base fees reduce inventory, and actual allocated basis determines realized PnL, including losses. A full close clears residual basis exactly. No SQLite REAL monetary arithmetic or SQL SUM is used.

Fill identity is scoped by symbol within the account store and checked against an immutable payload fingerprint, client intent and exchange order ID. Canonical decimal formatting makes equivalent numeric replays idempotent. A global normalized event sequence detects missing/out-of-order facts. The financial savepoint rolls back all balance, order, daily and stop changes together while retaining a pending receipt and hold. Missing fees, third-currency fees, negative rebates, identity conflicts, overfills, limit violations and reservation conflicts cannot silently alter cash. Unmatched receipts are retained without inventing an order.

Late fills after cancellation/rejection are retained and applied only if accounting invariants permit, then the account is held for authoritative lookup. An elapsed timer never proves an order cancelled. Financial recovery deliberately has no TTL release; news work leases below have no monetary meaning.

The offline normalized-input contract is not an exchange proof mechanism. A future adapter must authenticate account ownership, map stable provider identities, establish complete ordered fill/fee facts, validate event times, reconcile balances and handle pagination/reconnect gaps. It must replace optimistic caller bookkeeping rather than wrap it.

## Advisory news implementation

| Component | Behavior |
| --- | --- |
| `backend/trading/news_schema.py` | Explicit dedicated `state/crypto_news_telemetry.db`, separate from execution stores. WAL/FULL, immutable article identity, atomic claims, persistent three-attempt retry budget, 30-second processing lease, bounded retention and per-feed health. Import and GET never create it. Fixtures have separate provenance. |
| `backend/daemons/news_catalyst_daemon.py` | Concurrent feed polling and independent analysis queue. Configured CoinDesk, CoinTelegraph and Decrypt public RSS. Normal polling45s; failures back off30–300s per source. Fixed HTTPS URLs, TLS verification, no redirects/cookies/environment proxies, response/time limits, no article-page fetch. XML entities/DTD and ambiguous encodings are rejected. |
| Local analysis | Explicit installed model and ticker allowlist are required. `127.0.0.1:11434/api/show` validates local metadata, then `/api/generate` uses the identical explicit local source. Both calls forbid redirects. Strict JSON schema/ranges/types reject malformed output; article text is untrusted prompt data. No model pull, cloud fallback or invented neutral success. |
| `backend/routers/news_catalyst_router.py` | GET `/api/telemetry/news-catalysts` only; bounded limit1–50, SQLite read-only/query-only. Missing database is explicit `not_configured`; wrong scope/corruption is unavailable. No model invocation or mutations. Mounted additively in `backend/AI_BS_Backend.py`. |
| `CryptoNewsCatalysts.jsx` | Read-only panel in all four `CryptoLiveStreamTab.jsx` mirrors. Poll45s after completion, abort after6s, cancel on unmount. Renders escaped text, stale/unconfigured/failure states and uncalibrated model confidence; no order controls. |

Only articles with a known publication time within the past hour are eligible for inference. Unknown, future and old dates remain explicit, without invented publication timestamps. Pending retries and expired processing claims recover even if the article disappears from the feed. Old lease tokens cannot overwrite a newer worker's result. Display requires recent analyzed data, an allowed token, non-NOISE category, absolute impact at least0.6 and model confidence at least0.7. These thresholds are display filters, not calibrated probabilities or evidence of predictive value.

The worker is not registered with the backend supervisor and has not been run. Its manual CLI requires `--database`, `--model` and `--symbols`; `--initialize` creates only a new dedicated news store. No existing legacy news firehose was reused: that path contains automatic buy behavior and remains outside this implementation. The existing gateway already forwards `/api/`; no gateway mutation was necessary.

Official references reviewed: [Ollama generation API](https://docs.ollama.com/api/generate), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [model source parser](https://github.com/ollama/ollama/blob/main/internal/modelref/modelref.go), [show/generate handlers](https://github.com/ollama/ollama/blob/main/server/routes.go), and [CoinDesk RSS guidance](https://www.coindesk.com/coindesk-news/2021/09/17/coindesk-rss). Current upstream source informed the explicit local-source contract; it does not establish the installed server version. Unsupported servers fail closed. CoinTelegraph/Decrypt URLs are configuration, not observed availability.

## Medium / Low risks and limits

- Signing vectors, durable authenticated nonce generation, secret lifecycle and exchange-specific rate/retry budgets are still prerequisites for a live adapter. The coordinator does not sign requests or hold secrets. No exchange mutation retry was introduced.
- Stored inputs are bounded and Decimal-based; repeating cost-basis division uses the explicit arithmetic context. No claim of arbitrary infinite precision or reconstructed historical fees is made. Third-currency fees and rebates require a reviewed valuation policy.
- Stale/missing quotes block risk decisions. A hard account hold also blocks protective submission decisions; it does not pretend an exit is placed. Existing exchange-side protections need independent reconciliation.
- RSS polling has fixed configured publisher destinations and bounded retries. Actual publisher responses, licensing/usage constraints, model latency/GPU suitability and local server compatibility remain unverified. No paid service or dependency installation was added.
- A worker poll being recent is not a general health guarantee. Failed analysis remains visible. Confidence is explicitly uncalibrated and advisory news cannot mutate trading state.
- The panel passed syntax checks; loaded application, browser layout and authenticated integration were not exercised. No full frontend build or mirror-wide synchronization was run.

## Gemini suggestions assessed

The durable-coordinator and public-RSS/local-inference architecture was useful. The pasted code was not adopted unchanged. It proposed floating-point financial storage, expiring ambiguous order reservations, random receipt identities, non-atomic reservation checks, a canonical control-database default, blocking feed fetches and failure-to-neutral results. Those properties were excluded. Speculation about NTFS corruption or exact causes of ledger divergence remains unproven; no move/delete/reconstruction or removal of the live hold followed from it.

## Verification and evidence

**68 focused offline tests passed in6.918s:**36 execution-control tests,19 news tests and13 existing containment tests. The exact command was:

```powershell
.\pyppeteer_env\Scripts\python.exe -m unittest scripts.tests.test_crypto_execution_controls scripts.tests.test_crypto_news_catalysts scripts.tests.test_crypto_integrity_containment -v
```

The tests use explicit synthetic feed/model/fill facts, temporary stores and an isolated ASGI app. They cover partial/duplicate/late fills, fees and loss accounting, restart/unknown recovery, transactional failure, concurrent reservations, rejection generations, drawdown, per-quote and first-fill trailing protection, stop generations, strict inputs, news dedup/claims/recovery/rate bounds, local-only transport rules and read-only API behavior. Paper-fixture log lines in the existing containment suite are not live execution evidence.

Checkpoint `backups/crypto_execution_controls_20261030T185003Z` retains original bytes, before/after manifests, exact patch, raw tests, diagnostics and scoped verification. Final checks cover10 Python AST parses, both changed JSX components, four-mirror SHA-256 parity, unchanged source hold and exact monetary JSON hashes. The report and checkpoint are engineering evidence, not a release or live-trading acceptance.

## Remaining live gates

1. Preserve containment; reconcile existing orders, fills, fees, balances and ledger provenance against authoritative exchange evidence.
2. Implement a provider adapter with signing/nonce vectors, read-only recovery, complete normalized fill facts and bounded rate handling. Replace all optimistic legacy accounting and route every account worker through one shared coordinator.
3. Validate authenticated controls, stop/cancel/partial recovery, operational rejection/reset policy and durable production-store migrations using recorded provider contracts before live acceptance.
4. Separately validate loaded runtime bindings and existing exchange protections. News worker/model/feed and browser acceptance are independent of trading activation.

No live-enable mechanism, service restart, actual inference/feed poll, environment/activation flag change, model/dependency install, data repair, commit or publication occurred.
