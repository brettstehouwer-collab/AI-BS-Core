# Realistic local writing timing baseline — October 24, 2026

One fixed synthetic community-workshop announcement was measured through the existing direct loopback model API. Ten comparable warm requests completed, with zero runtime failures. Every response missed the requested paragraph length. Successful inference completion is therefore distinct from writing-instruction compliance.

This adds one realistic text-generation condition to the Phase 6 benchmark sheet. It does not establish application workflow, general model quality, offline resilience or VM acceptance.

## Observed results

| Condition | Requests | Completed | Median elapsed | P95 elapsed | Median first text | P95 first text |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Identical warm workshop-announcement request | 10 | 10 | 8.478690 s | 8.863537 s | 0.109921 s | 0.132382 s |

P95 uses the nearest-rank method. With ten samples, it is the largest observation, rather than a high-confidence production percentile. All ten streams ended with `done=true` and `done_reason=stop`; none reached the 256-token output cap. Each warm response generated 102 tokens. The ten warm outputs had the same text hash.

Before those ten requests, one separate first-current-observation request took 24.446721 seconds, with first text at 15.675337 seconds. The model was absent from the live loaded-model list immediately beforehand. Server-reported loading took 14.100628 seconds and prompt evaluation took 1.544073 seconds. This is one load observation, not a true cold-run distribution or a controlled cold-cache measurement. It generated 104 tokens and its text differed from the subsequent warm response.

Total retained requests: eleven; eleven terminal completions; zero runtime failures; no retries or repairs. The first-current observation is excluded from warm statistics.

| Server-reported warm metric | Median | P95 |
| --- | ---: | ---: |
| Total duration | 8.470562 s | 8.846414 s |
| Load duration | 0.005061 s | 0.009179 s |
| Prompt evaluation duration | 0.083618 s | 0.097154 s |
| Generation duration | 8.368329 s | 8.735627 s |

Server timing fields were converted from nanoseconds. Client elapsed time includes request/stream receipt; first text is measured from request start to the first nonempty response-text chunk. It is distinct from first network byte or a server-side first-token timestamp.

## Condition and instruction compliance

The frozen 534-byte synthetic prompt asks for a headline and an 80–100-word promotional paragraph about an invented studio and town, using fixed event, price and capacity facts. It includes no real private project, manuscript, customer, account or contact data. The exact prompt and request bytes remain in the local evidence directory; the request SHA-256 is `33e93b1e3853b8c3483516e260599a24f3f08d9a4025e7b55de7148e67d20f2a`.

Whitespace counting found 76 words in each complete response: seven in the headline and 69 in the paragraph. All eleven responses therefore failed the requested paragraph-length constraint. No prompt change or automatic repair was used to improve that result. Other content quality and factual-instruction compliance were not comprehensively scored. A terminal completion must not be reported as a creative-quality pass.

## Runtime conditions and preservation

- Existing `stehouwer_llm:latest`, 32.8B/Q5_K_M; digest `5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12`, unchanged before and after.
- Existing Ollama 0.40.9 at `127.0.0.1:11434/api/generate`; streamed requests; context 4096; temperature 0; seed 42; output cap 256 tokens; keep-alive five minutes. The server reported 2027 evaluated prompt tokens for each request; this differs from the caller's prompt byte count. No model template was exported.
- AMD Ryzen 9 9950X, 32 logical processors, approximately 66.19 GB physical RAM and NVIDIA GeForce RTX 4090. Per-request CPU, available RAM and GPU observations are retained. Other host activity continued; concurrent load was observed, not controlled. Repeated-prompt cache reuse was allowed and not independently quantified.
- Fresh service observations identified backend PID 80276, gateway 25576, frontend 111704 and model server 148912, each listening only on `127.0.0.1`. Those exact before/after process creation times, executable paths/hashes and six false activation flags matched during this measurement. This is a fresh observation window, not an inference from historical checkpoint PIDs.
- Twenty-one selected source/version/driver/model-manifest hashes matched before and after. The prior arithmetic driver remains unchanged, with a retained copy. No model selection, pull, unload, restart, configuration/flag change, VM operation or generated-code/task execution occurred.

## Evidence, bounds and limits

Evidence is local at `C:\AI-BS\backups\phase6_realistic_baseline_20261024T193545Z`. It contains the retained prior driver, frozen measurement driver/prompt, request metadata, eleven raw streams and per-request records, hardware/load observations, before/after identity hashes, summary and independent raw-evidence verification. The completed execution session was 93166; launcher PID 60576 and actual Python child PID 141388 were observed while running. The session exited zero.

An independent verifier reconstructed response hashes and terminal metrics from all eleven streams, checked request/model identity and warm-load observations, and recalculated median/P95 from the ten completed warm records. Largest observed stream: 21,304 bytes; largest line: 10,154 bytes. Every actual request completed within 180 seconds.

The driver attempted a 180-second client deadline, a 64-KiB line bound and a 1-MiB stream threshold, stopping on the first runtime failure. Read-only review identified two generic implementation edges for future reuse: the stream threshold is checked after one bounded line is written, and a closing HTTP response can clear the connection's socket reference used by its watchdog. The measured streams stayed far below either limit; this run does not certify hard timeout/cancellation enforcement or prove upstream generation stops after client disconnect. Preserve this frozen driver as executed; harden those edges before relying on it as a general failure-boundary test.

One ancillary hardware/process observer initially used an unsupported `Set-Content -NoClobber` parameter and wrote neither target file. It was corrected once using exclusive file creation; the error/correction is retained separately and affected no inference request.

Raw streams can include context token IDs. Keep raw/context-bearing evidence private and local; do not copy it into the engineering cloud ledger or a public demonstration. This report contains only summarized conditions, constraints and metrics. No external endpoint was contacted by the benchmark, but host networking remained connected. Offline capability, isolated execution, end-to-end repair/review/apply/cancel/recovery, competitive performance and remaining Phase 4–6 gates are still unverified by this measurement.
