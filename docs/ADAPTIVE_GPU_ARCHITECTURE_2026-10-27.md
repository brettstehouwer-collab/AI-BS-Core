> Historical Record150 document, retained below. The later 621.01 stock software increment and current acceptance limits are in [Record164 provision results](ADAPTIVE_GPU_PROVISION_RESULTS_2026-10-27.md). The following driver observations and decisions describe the earlier checkpoint.

# Adaptive GPU architecture — 2026-10-27

The stock Windows GPU configuration remains the production configuration. The
new adaptive admission path is implemented but **disabled by default** pending
measured workload acceptance. The production dispatcher enables it only when
`AIBS_ADAPTIVE_GPU_ENABLED` is exactly `true`, read when its singleton is created.
A standalone `OllamaDispatcher(enabled=True)` supports explicit benchmark runs
without enabling production admission or restarting services.

## Implementation map and scope

| Source | Responsibility |
| --- | --- |
| `backend/gpu/gpu_telemetry.py`, `hardware_inventory.py` | Read-only device identity, memory, temperature, power and software inventory; unavailable values remain unavailable. |
| `backend/gpu/compute_scheduler.py`, `vram_manager.py` | Bounded priority admission, local reservations, explicit profiles, cancellation cleanup and bounded latency observations. |
| `backend/gpu/stability_supervisor.py` | Telemetry freshness, memory consistency, thermal/power admission checks and externally supplied real-time pressure. |
| `backend/gpu/model_residency.py` | Observed Ollama residency and bounded, ordered embedding batches. |
| `backend/gpu/precision_router.py` | Advisory backend capability recommendations only. |
| `backend/orchestrator/gpu_task_dispatcher.py` | Local Ollama discovery, conservative incremental estimates, post-grant residency checks, rollout gate and inference option bounds. |
| `backend/gpu/benchmark_runner.py`, `scripts/adaptive_gpu_benchmark.py` | Retained stock benchmark records, CUDA matrix measurements and bounded local inference comparisons. |

The public controller API is `get_controller()`, an asynchronous
`controller.lease(model, workload="chat", estimated_vram_mib=..., priority=10)`
context manager, and `await controller.snapshot()`. Construction has no device,
database, worker or service startup side effects. Status reads do not activate
services. The default telemetry provider reads memory through optional NVML,
caches slower sensors for at most two seconds, and falls back to a bounded
`nvidia-smi` query. The subprocess uses argument lists, no shell and a timeout.
Admission refreshes memory rather than relying on the status cache. Missing,
stale or inconsistent required telemetry fails enabled admission closed.

Loopback HTTP metadata clients reuse a certificate-checking TLS context instead
of repeatedly loading the Windows certificate store. HTTPS and remote endpoints
are rejected before I/O. This reduces measured metadata setup cost; inference
performance after this correction has not been measured. Cached telemetry
advances both allocation and sensor ages rather than relabeling older sensors
as fresh.

Coverage is limited to callers using the adapter: normal chat streaming and
nonstreaming in `backend/routers/chat_router.py`, primary/fallback agent calls in
`backend/routers/agent_routing.py`, and the chat router's GPU embedding fallback.
The embedding secondary explicitly requests `num_gpu=0`; a port number alone
does not establish CPU execution. Both configured endpoints are validated as
loopback HTTP before model discovery or CPU embedding input is sent, including
when adaptive admission is disabled. Coding request admission still runs before
normal chat GPU work; this change does not grant project execution authority or
change an explicit Windows VM selection.

Direct Ollama callers remain outside admission, including
`backend/core/coding_chat.py`, `backend/core/project_rag.py`,
`backend/routers/screenwriting_router.py` and `backend/routers/novelizer_router.py`.
This is a cooperative, process-local scheduler. It neither coordinates separate
backend processes nor imposes a driver memory quota on Ollama, games, DAWs,
desktop applications or other GPU users. Device telemetry includes their usage,
but cannot reserve resources against their future allocations.

## Admission, profiles and residency

| Profile | Total VRAM fraction | Extra reserve | Admission temperature limit | Maximum active leases | Maximum keep-alive |
| --- | ---: | ---: | ---: | ---: | ---: |
| balanced (default) | 0.80 | 512 MiB | 85 C | 1 | 300 s |
| realtime | 0.55 | 768 MiB | 82 C | 1 | 120 s |
| ai_compute | 0.92 | 512 MiB | 85 C | 1 | 300 s |
| experimental (unavailable) | 0.85 | 768 MiB | 82 C | 1 | 120 s |

Profiles are explicit internal selections. There is no automatic runtime mode
switch and experimental activation is rejected. The available budget is the
smaller of reported free memory and the profile fraction minus observed used
memory, with the profile reserve and local active reservations subtracted.
Admission also rejects estimates exceeding the entire profile allowance.

The default queue holds at most 32 pending requests and waits at most 30 seconds.
Lower numeric priority wins, then FIFO order. Cancellation, exceptions and normal
context exit release local reservations. Admission timeout does not preempt an
already running inference; the caller owns its request timeout. Fresh telemetry
awaits use the remaining admission deadline and return `telemetry_timeout` when
exceeded. Cancelling that await cannot terminate an in-flight native NVML worker.
Snapshot p50,
p95 and p99 queue/lease latencies use at most 256 recent samples, not sustained
end-user service guarantees.

Enabled dispatcher requests default to `num_ctx=4096` and `num_batch=512`, cap
context at 8192 and batch at 512, and accept bounded integer GPU-layer options.
Callers bind the returned options and profile keep-alive to the inference
payload. Disabled admission preserves omitted legacy context/batch options and
returns the existing 300-second keep-alive bound.

The desired memory estimate in MiB is
`ceil(disk_weight_bytes / 1048576 * 1.10) + 1024 + max(1024, ceil(num_ctx / 1024) * 512)`.
Incremental admission subtracts validated, observed model `size_vram` bytes,
capped at that desired estimate, with a 768 MiB minimum reservation. Nonzero
residency does not prove that requested layers or context are already loaded.
Every grant rechecks `/api/ps`; increased incremental demand releases and
reacquires admission, with at most three grants before a typed failure.
Disk size and the context margin remain estimates: model-specific KV geometry,
reload peaks and external contention prevent a memory safety guarantee.

Residency is observed rather than managed through eviction. The controller does
not unload, pull, preload or evict other users' models. Keep-alive is bounded and
no automatic model replacement is introduced. Embedding batches retain input
order and reject oversized individual inputs instead of silently truncating them.

Ollama precision remains backend-managed. The precision module preserves model
quantization and sends no dtype override; it does not prove Tensor Core use or
implement FP16/BF16/TF32 kernel routing. Supported-dtype recommendations for
other backends still require a real integration and numerical validation.

Real-time pressure requires actual audio/video latency, deadline and underrun
observations supplied to `record_realtime_observation`. Recent violations defer
background/chat admission and allow eligible audio/video/realtime queue entries
to proceed. Existing work is not preempted. DAW callbacks, capture timestamps,
NVENC paths and device underrun counters still need instrumentation before any
audio/video latency or isolation claim.

## Benchmark acceptance gates

Retain the original failed or incomplete runs alongside reruns. Stock baseline
and admitted stock tests must use the same installed model digest, quantization,
context, batch size, prompts, seed, output bounds and warm-up policy. Alternate
condition order and record background activity and cache confounds. Report load,
wall time, prefill and decode rates separately; cached prefill is not an uncached
throughput measurement. Synthetic concurrent requests are not completed agent
tasks. CUDA GEMM results are not firmware-unlock attribution.

Production enablement requires repeatable application throughput or latency
benefits without unacceptable p95/p99 delay, numerical/quality degradation,
out-of-memory errors, thermal/power violations or real-time underruns. Establish
workload-specific thresholds before acceptance and include direct bypass callers
in contention testing. A small smoke run, passing offline tests or a healthy
status endpoint does not establish release acceptance. Image generation and
physical audio/video acceptance remain unmeasured until fixed workloads and
their actual device instrumentation are admitted.

## Separate native Linux preparation gate

Experimental research is anchored to upstream revision
[`d28c485418c3d9d034cd4bac19200bc33dd3453b`](https://github.com/JustAResearcher/gpu-unlock-ada/commit/d28c485418c3d9d034cd4bac19200bc33dd3453b).
The pinned `QUICKSTART.md`, `docs/evidence/rtx4090-pr1-matched/README.md`,
`windows/ad104-msi/README.md` and `firmware/artifacts-610.43.03.json` have different
platform/device evidence scopes; none establishes acceptance for this host.

Preparation remains a separate checklist, without automatic activation:

1. Preserve current Windows, model and project data; establish a genuinely
   separate native Linux installation and a stock boot path independent of any
   experimental path. WSL provides a virtualized CUDA environment and is not a
   substitute for native pre-driver preparation.
2. Verify independent boot, device display access and recovery using the stock
   configuration first. Record board identity, exact firmware/driver versions,
   image provenance and rollback readiness. This recovery path is **not verified
   here**.
3. Review the pinned source and its exact compatibility/evidence matrix before
   considering a bounded experiment. Current Windows observations are RTX 4090,
   PCI device `10de:2684`, NVIDIA `617.42`, VBIOS `95.02.20.00.01`; that combination
   remains unvalidated against the pinned upstream evidence. A matching PCI ID
   alone is insufficient.
4. Preserve a native stock baseline and define separate synthetic, numerical,
   inference, thermal and recovery acceptance criteria. Any later experimental
   execution needs its own explicit scope and verified recovery prerequisites.

Official lookup identified NVIDIA desktop driver 617.42, released 2026-10-06,
through the [Game Ready listing](https://www.nvidia.com/en-us/drivers/details/280103/)
and [Studio listing](https://www.nvidia.com/en-us/drivers/details/280135/).
No newer applicable release was established by that lookup. Requery official
driver listings for any follow-up because availability changes. No driver update,
firmware command, boot modification or firmware modification was run as part of
this implementation. This document supplies no executable exploit instructions,
scripts or download workflow. The Windows production GPU configuration is unchanged.
