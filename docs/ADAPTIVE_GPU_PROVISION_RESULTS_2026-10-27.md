# Stock GPU provision increment — 2026-10-27

The local software increment is implemented and measured with NVIDIA 621.01.
Reusing a validated loopback HTTP client context reduced median client-path wall
time from 537.5 ms to 352.6 ms in six paired small-model trials, a 34.39% reduction.
HTTP inference time itself was essentially unchanged. This is an application
transport improvement, not faster Tensor Core execution or a driver speedup claim.
The running backend has not been restarted to load these source changes.

Adaptive GPU admission remains disabled in production. Its corrected stock
comparison showed median request latency +0.51%, p95 +14.64%, and synthetic
concurrent throughput +2.85%. These small samples do not establish the sustained
benefit, tail latency, quality, or physical media acceptance required to enable it.
The separate Linux/recovery and experimental unlock steps remain deferred.

## Changes and retained evidence

- `backend/core/local_ollama_http.py` validates loopback HTTP origins before
  client construction and actual requests. It reuses an SSL context with
  `CERT_REQUIRED` and hostname checking enabled, keeps `trust_env=False`, and
  preserves caller timeouts. Other remote HTTP clients retain their behavior.
- Chat metadata, embedding, streaming/nonstreaming chat, agent inference, and
  dispatcher metadata use the factory. Streaming resources and cancellation
  cleanup remain covered by offline tests.
- Chat arbitration now runs through `asyncio.to_thread`. The existing GPU/ComfyUI
  probes and routing decisions remain intact, while the ASGI event loop can
  progress during a blocked probe. This does not remove the probe's own latency.
- The stock benchmark supports exact installed model/digest pins, phase
  selection, six paired trials by default, AB/BA ordering, and both concurrency
  orders. It checks health, budget, selected digests and residency before model
  requests, and refuses unrelated resident models rather than evicting them.
  Numerical and malformed embedding failures retain terminal failure receipts.
- Originals, scoped diffs, red/green test logs, incomplete test attempts and
  source hashes are under `backups/adaptive_gpu_provision_20261027`. No shared
  checkout reset, cleanup, commit, service restart or model download was used.

The controller comparison used the script captured in
`benchmark_originals/stock_controller_run_source.py`. Its source and result hashes
are bound in `stock_controller_run_source_binding.json`. Subsequent offline fixes
reject resident digest mismatches and numerical/embedding validation failures;
they do not change this run's valid measured samples. The original Record150
reports and regressing attempts remain preserved.

## Host and protocol

Fresh read-only inventory confirmed RTX 4090, PCI `10de:2684`, 24,564 MiB physical
VRAM, VBIOS `95.02.20.00.01`, driver 621.01 and the unchanged 450 W limit.
Python is 3.12.10, PyTorch 2.5.1+cu121 and Ollama 0.40.9. The driver update is
verified separately in `backups/nvidia_driver_update_20261027`; the optional
NVIDIA App installation failure remains separate from the installed driver.

Both comparisons used installed `llama3.1:8b-instruct-q5_K_M`, digest
`27fe1b0ab52c0027e30f4a007d2137b451af6021a53485959a961b0fe84ce2dc`,
temperature 0, seed 42, context 2048, batch 512, output bound 48 tokens, warmups
excluded, six paired prompts and alternating condition order. The client-path
comparison created a client for each `/api/chat` request; the controller
comparison reused one client for `/api/generate`. They measure different costs
and must not be combined into an overall speedup.

The first cold client-path warmup took 52.45 s, including reported model load
32.50 s. It was excluded explicitly; warm results do not promise cold-start gains.
Initial residency was empty, no matching DAW/OBS/Unreal process was observed, and
the only admitted model operations were bounded synthetic benchmark requests.
Existing one-model/one-parallel-request/flash-attention settings were retained.

## Measurements

| Measurement | Baseline | Revised/admitted | Interpretation |
| --- | ---: | ---: | --- |
| Client construction median | 186.930 ms | 0.087 ms | Repeated Windows CA-store construction avoided |
| Client-path wall median | 537.485 ms | 352.641 ms | 34.39% reduction in this warm 8B smoke |
| Client-path HTTP median | 352.334 ms | 352.402 ms | Inference transport duration essentially unchanged |
| Controller request wall median | 401.704 ms | 403.752 ms | +0.51% |
| Controller request wall p95 | 440.615 ms | 505.123 ms | +14.64%; only six samples per condition |
| Controller admission median | 0 | 12.895 ms | Cooperative scheduling/metadata cost |
| Synthetic concurrent completions/s | 2.0159 | 2.0734 | +2.85%, two rounds of three requests per condition |
| Stock 2048-cubed FP16 GEMM | — | 152.04 TFLOP/s median | FP32-reference relative L2 error 0.000206; tolerance 0.002 passed |
| Stock 2048-cubed BF16 GEMM | — | 150.94 TFLOP/s median | Relative L2 error 0.001670; tolerance 0.02 passed |

Controller health snapshots sampled up to 49 C, 283.24 W and 8,062.84 MiB used.
These are sampled observations, not continuous thermal/power peaks or a stress
test. Its active/queued/reserved counts ended at zero with no rejected lease.
Per-request benchmark preflight costs were recorded separately from request wall
time; concurrent batch wall time includes them.

Client-path output hashes matched in 4/6 pairs and controller hashes in 3/6 pairs.
Temperature zero does not establish identical output or quality. KV cache was
not flushed; balanced order reduces unequal exposure but reported prefill rates
cannot establish uncached-prefill performance. Synthetic concurrent inference is
not completed autonomous agent work. Earlier runs used a different driver and
protocol, so the new decode rates cannot be attributed to the driver update.

Raw measurements: `client_path_run/receipt.json` and
`stock_controller_run/benchmark_results.json` under the evidence directory.

The separate admitted embedding smoke used pinned `nomic-embed-text:latest`,
digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.
It returned 8 ordered vectors of 768 finite values each in 24.52 s HTTP wall
time, with admission 82.13 ms. The count/shape checks passed. This single cold
batch establishes neither embedding speedup nor semantic quality. It used only
our admitted benchmark models; no unrelated resident was displaced. Receipt:
`embedding_run/benchmark_results.json`.

## Source verification

The final combined offline suite passed **100 tests in 4.933 s**, covering
controller budgets/leases, fresh telemetry, dispatcher integration, benchmark
receipt retention/health/digest/numerical checks, metrics, strict local clients,
streaming cleanup, coding isolation short circuit and event-loop progress during
arbitration. The full log is `combined_green.log`. These tests use synthetic or
mocked I/O and are separate from the three live stock benchmark receipts.
Retained failures include the initial missing-FastAPI interpreter attempt and
corrected test fixtures; they were not erased or relabeled as successful runs.

## Activation and remaining gates

Source verification and bounded benchmark execution are complete for this
increment; production activation is pending a coordinated backend release. The
shared checkout contains unrelated RecDebut source work, so a restart would load
more than this change. No running services were replaced to activate it.

Before global adaptive admission, establish workload-specific thresholds and
repeat accepted default-model, stream cancellation, direct bypass contention,
numerical/quality, loading-peak, and actual audio/video deadline/underrun tests.
The roughly 23.26 GB default model, image generation and real physical media
latency remain unaccepted. The scheduler is process-local/cooperative, and
precision advice does not itself select kernels or rewrite model quantization.

The upstream research revision remained
[`d28c485418c3d9d034cd4bac19200bc33dd3453b`](https://github.com/JustAResearcher/gpu-unlock-ada/commit/d28c485418c3d9d034cd4bac19200bc33dd3453b)
on the fresh public metadata check. Its
[README](https://github.com/JustAResearcher/gpu-unlock-ada/blob/d28c485418c3d9d034cd4bac19200bc33dd3453b/README.md)
distinguishes instruction-throughput results from application results and
documents platform-specific evidence. It does not establish this Windows
RTX 4090 / 621.01 configuration as accepted. No experimental firmware, UEFI,
boot-media, clock, power or Linux disk operation was performed.

The [HTTPX SSL documentation](https://www.python-httpx.org/advanced/ssl/)
supports supplying an SSL context; the new factory additionally rejects HTTPS
and remote origins before transport. Existing Ollama resource controls follow
the [Ollama configuration reference](https://docs.ollama.com/faq) but were not
changed by this increment.
