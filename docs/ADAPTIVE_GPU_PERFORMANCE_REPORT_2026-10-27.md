> Historical Record150 document, retained below. The later 621.01 stock software increment and current acceptance limits are in [Record164 provision results](ADAPTIVE_GPU_PROVISION_RESULTS_2026-10-27.md). The following driver observations and decisions describe the earlier checkpoint.

# Adaptive GPU implementation and performance report — 2026-10-27

## Decision

Keep stock Windows GPU operation and keep adaptive admission **disabled by
default**. The controller and bounded chat/agent/embedding integrations are
implemented, but the two retained application smoke comparisons regressed.
No application speedup or unlock benefit is established for this computer.
Experimental firmware execution and native Linux acceptance remain pending.

The implementation is described in
[the architecture record](ADAPTIVE_GPU_ARCHITECTURE_2026-10-27.md). Evidence is in
`backups/adaptive_gpu_20261027_record147`. That directory was named before
concurrent RecDebut records were finalized; its name is retained. This GPU
checkpoint is **Record150**, separate from RecDebut Records147–149.

## Verified host and runtime

| Item | Observed value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 4090, PCI `10de:2684`, 24,564 MiB physical VRAM |
| Driver / VBIOS | NVIDIA 617.42 / Windows 32.0.16.1742; VBIOS 95.02.20.00.01 |
| Power limit | 450 W; unchanged |
| CPU | AMD Ryzen 9 9950X, 16 cores / 32 logical processors |
| Memory | 64,641,804 KiB visible, approximately 64 GB installed; the directive's 32 GB description differs |
| OS | Windows 11 Home, 10.0.26300 |
| Python / PyTorch | 3.12.10 / 2.5.1+cu121 |
| CUDA | PyTorch runtime 12.1, CUDA and BF16 available; standalone `nvcc` absent |
| Ollama | 0.40.9, local 127.0.0.1:11434 |
| Existing Ollama controls | One loaded model, one parallel request, flash attention enabled; startup configuration unchanged |

Task Manager's 69.6 GB combined GPU memory includes shared system memory. It is
not 69.6 GB of physical VRAM. The inventory does not independently establish the
board as Founders Edition or verify memory clock specifications.

The fixed LLM was `llama3.1:8b-instruct-q5_K_M`, 5,733,006,512 bytes, digest
`27fe1b0ab52c0027e30f4a007d2137b451af6021a53485959a961b0fe84ce2dc`.
The embedding model was `nomic-embed-text:latest`, digest
`0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`.
No model was pulled, deleted or replaced. The existing approximately 23.26 GB
32.8B Q5 default model was not accepted under the enabled controller; its
CPU-offload and loading peaks need a separate bounded comparison.

## Implemented behavior and limits

- Priority/FIFO admission with 32 pending slots, a 30-second wait, one active
  lease, fresh memory observations, profile budgets and cancellation cleanup.
- Read-only NVML telemetry with bounded `nvidia-smi` fallback, sensor freshness,
  thermal/power checks and rolling queue/lease percentiles.
- Conservative incremental VRAM estimates, observed model residency,
  post-admission residency rechecks and bounded keep-alive. Residency does not
  automatically evict, preload or unload models.
- Ordered embedding batches capped at eight inputs and 16,000 characters;
  enabled admission can reduce input count according to available memory.
- Chat stream/nonstream and agent primary/fallback leases; explicit CPU
  embedding requests on the secondary path. Coding requests retain their
  execution-backend admission before ordinary chat GPU work.
- Controller status at `GET /api/v1/hardware/gpu/controller`; no new visible
  dashboard panel or signed-in application walkthrough is claimed.
- Backend precision recommendations remain advisory. Ollama controls actual
  quantized kernels; no FP16/BF16/TF32 override or automatic kernel routing was
  implemented. Physical audio/video counters are not integrated.

Admission is cooperative and process-local. Direct callers such as coding RAG,
screenwriting and novelizer remain outside it, and desktop applications can
allocate GPU memory independently. Estimates are not a driver quota or an OOM
guarantee. Real-time observations can defer new background work; running
inference cannot be preempted. Default-off operation avoids applying these new
limits to the unvalidated large-model production workload.

## Retained stock application measurements

Both runs used stock firmware, five trials per condition, one warm-up per
condition, alternating order, paired synthetic prompts, seed 42, temperature 0,
context 2,048 and at most 48 generated tokens. These are small smoke samples.
The receipt condition name `stock_optimized` means governed admission; it does
not establish an improvement.

| Metric | Run 1 baseline → governed | Run 2 baseline → governed |
| --- | ---: | ---: |
| Median request wall time | 0.7537 → 1.0118 s (**+34.2%**) | 0.7256 → 1.2771 s (**+76.0%**) |
| p95 request wall time | 0.8296 → 1.1502 s | 0.7478 → 1.4412 s |
| Median decode rate | 70.96 → 71.48 tokens/s (+0.7%) | 71.57 → 68.33 tokens/s (−4.5%) |
| Three concurrent synthetic requests | 1.4162 → 0.9686 completed/s (−31.6%) | 0.9691 → 0.7241 completed/s (−25.3%) |
| Concurrent group elapsed | 2.1183 → 3.0973 s | 3.0956 → 4.1431 s |
| Reported median prefill | 7,752 → 19,261 tokens/s, cache-confounded | 7,889 → 18,544 tokens/s, cache-confounded |

Run 1: 16:47:06–16:47:47 UTC. Run 2: 16:56:05–16:56:36 UTC.
Do not infer increased autonomous agent throughput from these synthetic HTTP
requests. Both the local scheduler and Ollama currently serialize admitted
inference. Decode variation in five samples is not statistical acceptance.

### Comparison confounds and protocol correction

The two retained runs omitted `num_batch` in the baseline while the governed
path explicitly sent 512. They therefore do not isolate the scheduler's causal
effect. The current benchmark script requests 512 in both conditions; **that
corrected protocol has not been run live**.

Ollama KV caching was not flushed. In run 2, cached prompt counts were
`[5,359,7,359,7]` for baseline and `[359,7,359,7,359]` for governed, out of 360
reported prompt tokens. The apparent prefill increase is not an uncached
throughput gain. Paired output hashes matched in only three of five run-2 pairs;
hash identity is not a quality evaluation. Quantization, generation length,
cache exposure, background desktop activity, order and thermals need matched
controls in a later comparison. Load durations were roughly 4–10 ms in run 2;
these measurements do not establish cold-load behavior.

Both runs recorded no benchmark exceptions and ended with no active or queued
leases. This is not sustained stability, GPU-reset monitoring, OOM acceptance,
memory leak acceptance or desktop application acceptance.

## Matrix and embedding smoke measurements

CUDA events measured 2,048-square cuBLAS GEMM, five warm-ups, five samples of
20 inner iterations. TF32 was temporarily disabled for the FP32 comparison and
the prior setting restored. The numerical reference uses a 256-square subset
of the already quantized inputs, accumulated in FP32.

| Measurement | Run 1 | Run 2 |
| --- | ---: | ---: |
| FP16 median | 149.60 TFLOP/s; 0.11484 ms | 148.08 TFLOP/s; 0.11602 ms |
| BF16 median | 147.43 TFLOP/s; 0.11653 ms | 147.36 TFLOP/s; 0.11658 ms |
| FP16 relative L2 error / limit | 0.000206 / 0.002, pass | 0.000206 / 0.002, pass |
| BF16 relative L2 error / limit | 0.001670 / 0.020, pass | 0.001670 / 0.020, pass |
| One embedding batch | 8 vectors × 768; 14.0878 s | 8 vectors × 768; 3.2360 s |

These matrix results establish only stock arithmetic smoke behavior. They do
not identify an unlock gain or establish LLM/image quality. Embedding durations
are single batches under different residency conditions; their difference is
not an accepted speedup. Input/output count passed; semantic retrieval quality
and corpus-indexing throughput were not measured.

Run-1 before/after snapshots: 27→29 C, 1,913→3,026 MiB used,
38.29→39.14 W. Run 2: 27→31 C, 2,301.6→3,496.5 MiB,
38.17→51.45 W. These are snapshots, not peak memory, peak power or sustained
thermal measurements. Physical audio/video p95/p99, underruns and image
generation were not measured.

## Diagnostic pivot after the two regressions

The two-strike rule stopped blind live reruns. Metadata-only diagnostics found
that constructing each default HTTPX client loaded the Windows certificate
store: 140.5–224.3 ms setup versus 1.6–11.4 ms for the local metadata request.
Fresh NVML cost was about 108 ms initially and 7.3–8.7 ms subsequently.

The adapter now reuses an empty TLS context with `CERT_REQUIRED` and hostname
checking intact for its strictly loopback HTTP metadata clients. Remote and
HTTPS endpoints are rejected before I/O. No production client uses
`verify=False`. Post-change metadata setup was 0.036–0.107 ms, total request
0.89–1.59 ms. Three empty enabled leases cost 292.75 ms initially and
13.71/11.06 ms warm, ending with zero reservations. These diagnostics performed
**zero inference requests** and do not prove that application regression is
resolved. A later live comparison must be separately bounded and retained.

## Upstream compatibility and driver findings

Research is pinned to unsigned upstream revision
[`d28c485418c3d9d034cd4bac19200bc33dd3453b`](https://github.com/JustAResearcher/gpu-unlock-ada/commit/d28c485418c3d9d034cd4bac19200bc33dd3453b),
reported version 1.1.1. The host's RTX 4090 PCI ID matches the Linux target;
Windows 617.42 and VBIOS 95.02.20.00.01 are not a verified compatible pair.
The pinned Linux path relies on pre-NVIDIA-driver boot preparation and specific
firmware inputs; current Windows and WSL observations do not validate it.

The upstream [matched RTX 4090 evidence](https://github.com/JustAResearcher/gpu-unlock-ada/blob/d28c485418c3d9d034cd4bac19200bc33dd3453b/docs/evidence/rtx4090-pr1-matched/README.md)
separates roughly doubled instruction-level throughput from cuBLAS ratios of
about 0.995–1.344× and quantized model serving without a demonstrated gain in
the matched modified-card comparison. One warm-reboot BF16 shape was about
8.2% slower. Those observations support workload-specific testing, not a
promise of doubled AI-BS performance or long-term stability.
The [Windows AD104 contribution](https://github.com/JustAResearcher/gpu-unlock-ada/blob/d28c485418c3d9d034cd4bac19200bc33dd3453b/windows/ad104-msi/README.md)
concerns a 4070 Ti/MSI platform and does not establish Windows RTX 4090 support.
See the retained research receipt for exact observed stacks and source links.
No upstream executable, driver, exploit or firmware payload was run here.

Official NVIDIA listings identify desktop [Game Ready 617.42](https://www.nvidia.com/en-us/drivers/details/280103/)
and [Studio 617.42](https://www.nvidia.com/en-us/drivers/details/280135/), dated
2026-10-06. Installed version 617.42 matches; no newer applicable release was
established in this lookup. Installed Game Ready versus Studio channel remains
unverified. Recheck official listings when updating; do not reinstall merely
to change the same version. No driver download, install, channel switch or
reboot was performed.

## Native Linux equipment and recovery gate

The operator connected a device described as a 500 GB Seagate ATA serial disk.
Windows disk and physical-drive queries still show only the existing internal
Samsung 2 TB, 1 TB and 512 GB NVMe devices. No Seagate target was identified.
Their existing Windows/data partitions must be preserved. A matching capacity
alone does not identify a safe installation target.

Connection type, the exact Seagate model, existing-data status and recovery USB
remain unverified. No disk was selected, initialized, repartitioned, formatted,
rescanned or reset. Native Linux creation cannot advance until the intended
device is detected and uniquely identified and any erase scope is explicit.
Then establish and test stock independent boot/display and recovery before an
experimental attempt. Retain a separate stock boot configuration and validate
physical cold-power recovery; warm reboot alone is not reset proof. Never
force-unload a driver while it owns active GPU/DMA work.

## Verification, preservation and remaining work

The final offline suite passed **75 tests and 71 subtests** in 3.81 seconds.
Coverage includes admission boundaries, reservation freshness, cancellation,
sensor ages, residency changes, router/stream failure cleanup, explicit CPU
embedding requests, ordered batching, execution-backend preservation,
rollout-off behavior, metric validation and failure-safe benchmark receipts.
Final review corrected telemetry waits that could exceed admission deadlines
and CPU embedding/model-discovery calls that bypassed endpoint validation.
Regression tests verify typed timeout cleanup and invalid configured endpoints
being refused before client construction or input transmission. Cancelling a
telemetry await cannot forcibly terminate an in-flight native NVML thread.
The benchmark runner refuses pre-existing output directories, atomically saves
checkpoints and retains terminal type/stage errors, interrupted samples and
failed temporary candidates. These are local synthetic tests, not release
acceptance. No frontend build was needed for this backend-only work.

Runtime verification at 17:06:02 UTC observed owned backend PID36280,
health 200, all six process activation controls false and adaptive GPU disabled;
8080/8000/11434/5173 bound only to 127.0.0.1, with 8888 absent. A concurrent
RecDebut chat performed its own backend reload; this GPU task restarted no
service. Earlier transient/mismatched identity probes are retained, superseded
by the fresh module/executable/creation-identity check. PIDs are dated evidence.

Original routers and checkpoint documents, two regressed receipts, diagnostic
receipts and test results are retained. No manuscript, personal database, model,
VM profile, network configuration, startup setting, firmware or version file
was intentionally modified. Source integration does not authorize worker
execution or host apply. VM containment and previous Phase 4 gates remain open.
Local ledger/checkpoint updates are separate from cloud synchronization, which
remains pending.

Remaining acceptance work:

1. Identify the Seagate and recovery media, preserve existing data, and verify
   stock native Linux boot/recovery before experimental consideration.
2. Run the corrected matched application protocol later, with cold/warm load
   separated, balanced cache exposure and actual queue/stream p95/p99. Retain
   every result; do not enable production if regressions remain.
3. Validate the default large model and CPU offload, direct-call contention,
   sustained memory/power/thermal behavior and measured GPU-reset/error signals.
4. Add actual DAW/capture underrun/deadline instrumentation and fixed image,
   speech, document-indexing and autonomous-agent task workloads.
5. Measure any isolated experimental result against its own matched native
   stock baseline and numerical/recovery criteria. Keep production stock until
   meaningful application benefits and reliability are established.

The evidence supports retaining this architecture as a gated foundation. It
does not support deploying the Tensor Core modification or enabling adaptive
admission in production today.
