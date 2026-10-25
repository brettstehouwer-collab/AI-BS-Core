# Local model timing baseline — October24,2026

Scope: one fixed synthetic arithmetic request through the existing direct loopback Ollama API. This is a repeatable measurement fixture, not application, coding, model-quality, offline-isolation, or platform acceptance.

## Observed results

| Condition | Samples | Completed | Median elapsed | P95 elapsed, nearest rank | Median first text | P95 first text |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Repeated warm request | 10 | 10 | 0.409493s | 0.550556s | 0.160062s | 0.338132s |

All ten returned exactly `42`, with terminal `done=true`. Actual generation was3tokens/2response characters per successful fixture request; the requested output cap was32tokens. This does not measure long-form reasoning or code generation. P95at n=10is the largest sample, not a high-confidence production percentile.

One successful cold/warm-up request took97.795827seconds, including server-reported46.505seconds model loading and51.000seconds prompt evaluation. The caller supplied a52byte prompt; the customized model's effective prompt evaluation counted1922tokens. No model template was exported. This one observation is not a cold-load distribution.

An earlier60second warm-up attempt timed out before receiving any bytes. The retained server log reports the client disconnected before loading finished and the load was cancelled; that attempt remains a failure. After diagnosing it, one separate attempt used a180second warm-up budget, followed by60second per-warm-request budgets. Total retained attempts across both directories:12;11completed and1failed. The successful ten-run warm condition has0failures. No repeated retry followed the timeout, and no latency figures were fabricated for the failed attempt.

## Conditions and evidence

- Existing `stehouwer_llm:latest`,32.8B/Q5_K_M; digest `5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12` unchanged after measurements.
- Ollama0.40.9, endpoint `127.0.0.1:11434`, context4096, temperature0, seed42, output cap32, streaming enabled, keep-alive5minutes.
- NVIDIA RTX4090; CPU/RAM details and before/per-request/after GPU samples retained in the checkpoint. Concurrent host load was observed, not fully controlled. Repeated-prompt cache reuse was allowed and not independently quantified.
- Initial failure: `backups/phase6_model_baseline_20261024T1638411889333Z`.
- Successful condition: `backups/phase6_model_baseline_20261024T1638411889333Z/attempt02_cold_load_budget`.
- Metadata, raw local NDJSON, per-request timings, hardware, failed warm-up, server excerpt, and aggregate summary are retained. Median/P95were independently recalculated from the10per-run files.
- Model output was never executed. No application chat history, personal databases, original documents, model definitions, activation flags, VM settings, or application source were changed by this benchmark. The four serving process identities and all six false process flags were freshly verified afterward.

Ollama documents streaming and nanosecond timing fields in its [generate API](https://docs.ollama.com/api/generate). Local measurements above come from retained actual responses, not documentation estimates.

## Remaining acceptance

No network was disconnected. This proves neither all-platform offline operation nor guest containment. Cold distributions, realistic coding/creative/business cases, end-to-end repair/review/apply/cancel/recover timing, controlled comparable conditions and any competitive comparison remain pending. Phase6is incomplete.
