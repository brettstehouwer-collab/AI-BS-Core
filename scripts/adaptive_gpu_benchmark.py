"""Bounded stock benchmark. No model download, clock changes, driver or firmware writes."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from gpu.benchmark_runner import cuda_matrix_benchmark, ollama_metrics, summarize
from gpu.hardware_inventory import collect_inventory
from gpu.compute_scheduler import get_controller
from orchestrator.gpu_task_dispatcher import OllamaDispatcher, admitted_options
from core.local_ollama_http import local_ollama_client
import httpx


def _save_receipt(output, receipt):
    """Commit within this run's directory; retain a failed candidate for diagnosis."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output,
                                     prefix=".benchmark_results.", suffix=".tmp", delete=False) as candidate:
        json.dump(receipt, candidate, indent=2, allow_nan=False)
        candidate.flush()
        os.fsync(candidate.fileno())
        candidate_path = candidate.name
    os.replace(candidate_path, output / "benchmark_results.json")


async def run(output, repeats, *, model_name=None, model_digest=None, phases=None):
    # Claim a fresh directory before collecting inventory or creating GPU clients.
    # Even an empty pre-existing directory belongs to an earlier attempt.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "aibs-gpu-benchmark-v1", "started": datetime.now(timezone.utc).isoformat(),
               "status": "running", "stage": "initializing", "configuration": "stock_firmware",
               "experimental_unlocked": {"status": "not_run", "reason": "no_verified_native_linux_recovery"},
               "audio_video_hardware_latency": {"status": "not_measured", "reason": "no_daw_underrun_or_capture_instrumentation"},
               "image_generation": {"status": "not_measured", "reason": "no_fixed_image_workload_admitted"},
               "health_checks": [],
               "failures": []}

    def checkpoint(stage=None):
        if stage is not None:
            receipt["stage"] = stage
        receipt["updated"] = datetime.now(timezone.utc).isoformat()
        _save_receipt(output, receipt)

    def finish(status, result):
        receipt.update(status=status, result=result, finished=datetime.now(timezone.utc).isoformat())
        checkpoint("complete")
        return receipt

    try:
        allowed_phases = ("matrix", "llm", "concurrency", "embeddings")
        if (isinstance(repeats, bool) or not isinstance(repeats, int) or not 3 <= repeats <= 10
                or isinstance(phases, str) or (phases is not None and
                    (not phases or any(phase not in allowed_phases for phase in phases)))):
            raise ValueError("invalid_bounded_benchmark_protocol")
        selected = tuple(phase for phase in allowed_phases if phases is None or phase in phases)
        if ((model_name is not None and (not isinstance(model_name, str) or not model_name.strip()
                                        or len(model_name) > 256))
                or (model_digest is not None and (not model_name or not isinstance(model_digest, str)
                                                  or not model_digest or len(model_digest) > 256))):
            raise ValueError("invalid_model_pin")
        for phase in allowed_phases:
            if phase not in selected:
                receipt["concurrent_requests" if phase == "concurrency" else phase] = {
                    "status": "not_run", "reason": "phase_not_selected"}
        checkpoint("inventory")
        receipt["platform"] = platform.platform()
        receipt["inventory"] = collect_inventory()
        host = "http://127.0.0.1:11434"
        controller = get_controller()
        dispatcher = OllamaDispatcher(enabled=True)

        async def check_health(label, *, snapshot_key=None):
            snapshot = await controller.snapshot()
            if snapshot_key:
                receipt[snapshot_key] = snapshot
            receipt["health_checks"].append({"stage": label,
                "observed": datetime.now(timezone.utc).isoformat(), "snapshot": snapshot})
            checkpoint()
            reason = None
            if not snapshot.get("health", {}).get("admission_available", False):
                reason = "gpu_health_unavailable"
            elif snapshot.get("stability", {}).get("realtime_pressure", False):
                reason = "realtime_pressure"
            elif "available_budget_mib" in snapshot:
                budget = snapshot["available_budget_mib"]
                if (isinstance(budget, bool) or not isinstance(budget, (int, float))
                        or not math.isfinite(budget) or budget <= 0):
                    reason = "vram_pressure"
            if reason:
                receipt["halt_reason"] = reason
                raise RuntimeError("benchmark_health_pressure")

        checkpoint("before_snapshot")
        await check_health("before_snapshot", snapshot_key="before")
        checkpoint("ollama_tags")
        async with local_ollama_client(host, timeout=120.0, client_factory=httpx.AsyncClient) as client:
            async def read_models(endpoint):
                response = await client.get(host + endpoint)
                response.raise_for_status()
                data = response.json()
                models = data.get("models") if isinstance(data, dict) else None
                if not isinstance(models, list) or any(not isinstance(item, dict) for item in models):
                    raise ValueError("invalid_ollama_inventory")
                return models

            def name_of(item):
                return item.get("name", item.get("model"))

            tags = await read_models("/api/tags")
            candidates = [m for m in tags if isinstance(m.get("size"), (int, float))
                          and not isinstance(m["size"], bool) and 0 <= m["size"] < 6_000_000_000
                          and isinstance(name_of(m), str)
                          and m.get("details", {}).get("family") not in {"nomic-bert", "bert"}
                          and "embed" not in name_of(m)]
            needs_llm = "llm" in selected or "concurrency" in selected
            model = None
            if model_name:
                requested = model_name if ":" in model_name else model_name + ":latest"
                model = next((m for m in candidates if name_of(m) == requested), None)
                if model is None:
                    receipt["halt_reason"] = "requested_model_not_bounded_or_installed"
                    raise ValueError("requested_model_not_bounded_or_installed")
            elif needs_llm and candidates:
                model = min(candidates, key=lambda m: m["size"])
            if needs_llm and model is None:
                receipt["llm"] = {"status": "unavailable", "reason": "no_bounded_installed_model"}
                return finish("incomplete", "stock_smoke_benchmarks_incomplete_no_bounded_installed_model")
            if model:
                if not isinstance(model.get("digest"), str) or not model["digest"]:
                    raise ValueError("missing_model_digest")
                if model_digest is not None and model["digest"] != model_digest:
                    receipt["halt_reason"] = "model_digest_mismatch"
                    raise ValueError("model_digest_mismatch")
                receipt["model"] = {k: model.get(k) for k in ("name", "digest", "size", "details")}
            embed = next((m for m in tags if isinstance(name_of(m), str)
                          and name_of(m).startswith("nomic-embed-text:")), None) if "embeddings" in selected else None
            pinned_models = [item for item in (model, embed) if item is not None]
            benchmark_names = {name_of(item) for item in pinned_models}

            async def check_residents():
                resident = await read_models("/api/ps")
                # Retain counts only: unrelated resident identities may be private.
                receipt["resident_preflight"] = {"count": len(resident),
                                                  "all_benchmark_models": all(name_of(m) in benchmark_names for m in resident)}
                if not receipt["resident_preflight"]["all_benchmark_models"]:
                    receipt["halt_reason"] = "nonbenchmark_model_resident"
                    raise RuntimeError("nonbenchmark_model_resident")
                pins = {name_of(item): item.get("digest") for item in pinned_models}
                if any(not isinstance(item.get("digest"), str)
                       or item["digest"] != pins[name_of(item)] for item in resident):
                    receipt["halt_reason"] = "resident_model_digest_mismatch"
                    raise RuntimeError("resident_model_digest_mismatch")

            async def guard(label, *, recheck_models=True):
                started = time.perf_counter()
                await check_health(label)
                await check_residents()
                if recheck_models:
                    current = await read_models("/api/tags")
                    for pinned in pinned_models:
                        observed = next((m for m in current if name_of(m) == name_of(pinned)), None)
                        if observed is None or observed.get("digest") != pinned.get("digest"):
                            receipt["halt_reason"] = "model_digest_changed"
                            raise RuntimeError("model_digest_changed")
                checkpoint()
                return time.perf_counter() - started

            # Metadata preflight precedes CUDA work and every model-loading request.
            await check_residents()
            checkpoint("ollama_version")
            response = await client.get(host + "/api/version")
            response.raise_for_status()
            receipt["ollama_version"] = response.json()
            options = {"seed": 42, "temperature": 0, "num_ctx": 2048, "num_predict": 48, "num_batch": 512}
            prompts = [f"Trial {i}. " + "The test robot sorts red, blue and green blocks into labeled trays. " * 24
                       + "Give three concise steps for checking the sorted trays." for i in range(repeats)]
            concurrent_order = [["stock_baseline", "stock_optimized"], ["stock_optimized", "stock_baseline"]]
            receipt["protocol"] = {"repeats": repeats, "phases": list(selected),
                                   "balanced_condition_order": repeats % 2 == 0,
                                   "warmup_per_condition": 1, "options": options,
                                   "prompt_sha256": [hashlib.sha256(p.encode()).hexdigest() for p in prompts],
                                   "condition_order": "alternating AB / BA paired trials (ABBA across each two trials)",
                                   "concurrent_condition_order": concurrent_order,
                                   "confounds": [
                                       "Same production GPU; uncontrolled background desktop activity and thermals.",
                                       "Both conditions explicitly request num_batch=512 and the same generation options.",
                                       "Ollama KV cache is not forcibly flushed; reported prefill may be cached, so it cannot establish uncached-prefill speedup.",
                                       "Paired prompts and odd repeat counts can give conditions unequal cache exposure despite alternating order.",
                                       "Governed wall time includes admission and metadata overhead; condition names do not imply a measured improvement.",
                                       "Output hashes record identity only; deterministic output equivalence and model quality are not established.",
                                       "Small sample smoke benchmark, not statistical or sustained acceptance."]}
            checkpoint()
            if "matrix" in selected:
                checkpoint("matrix")
                await guard("matrix")
                receipt["matrix"] = await asyncio.to_thread(cuda_matrix_benchmark, 2048, repeats)
                checkpoint()
                if any(result.get("numerical_pass") is False
                       for result in receipt["matrix"].get("dtypes", {}).values()):
                    receipt["halt_reason"] = "matrix_numerical_check_failed"
                    raise RuntimeError("matrix_numerical_check_failed")

            async def generate(prompt, governed):
                health_duration = await guard(receipt["stage"])
                payload = {"model": model["name"], "prompt": prompt, "stream": False,
                           "keep_alive": "5m", "options": dict(options)}
                start = time.perf_counter()
                admission_duration = 0

                async def request():
                    http_start = time.perf_counter()
                    response = await client.post(host + "/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not data.get("done") or data.get("error"):
                        raise RuntimeError("incomplete_generation")
                    return data, time.perf_counter() - http_start

                if governed:
                    async with dispatcher.lease(model["name"], host, workload="benchmark", options=options) as admission:
                        admission_duration = time.perf_counter() - start
                        payload["keep_alive"] = admission["keep_alive_s"]
                        payload["options"] = admitted_options(options, admission)
                        data, http_duration = await request()
                else:
                    data, http_duration = await request()
                return {**ollama_metrics(data, time.perf_counter() - start),
                        "admission_duration_s": admission_duration, "http_duration_s": http_duration,
                        "preflight_duration_s": health_duration}

            if "llm" in selected:
                receipt["llm"] = {"stock_baseline": [], "stock_optimized": []}
            if needs_llm:
                for governed in (False, True):
                    condition = "stock_optimized" if governed else "stock_baseline"
                    checkpoint("llm_warmup_" + condition)
                    await generate("Warm-up: answer with the word ready.", governed)
            if "llm" in selected:
                for index, prompt in enumerate(prompts):
                    for governed in ((False, True) if index % 2 == 0 else (True, False)):
                        condition = "stock_optimized" if governed else "stock_baseline"
                        checkpoint(f"llm_trial_{index}_{condition}")
                        receipt["llm"][condition].append(await generate(prompt, governed))
                        checkpoint()
            if "concurrency" in selected:
                receipt["concurrent_requests"] = {}
                condition_samples = {condition: [] for condition in concurrent_order[0]}
                for round_index, order in enumerate(concurrent_order):
                    for condition in order:
                        governed = condition == "stock_optimized"
                        checkpoint("concurrent_" + condition + (f"_round_{round_index}" if round_index else ""))
                        await guard(receipt["stage"])
                        start = time.perf_counter()
                        tasks = [asyncio.create_task(generate(f"Concurrent task {i}: list the numbers one through ten.", governed))
                                 for i in range(3)]
                        try:
                            samples = await asyncio.gather(*tasks)
                        finally:
                            # Stop sibling requests before committing a terminal receipt.
                            for task in tasks:
                                if not task.done():
                                    task.cancel()
                            await asyncio.gather(*tasks, return_exceptions=True)
                        wall = time.perf_counter() - start
                        condition_samples[condition].extend(samples)
                        result = receipt["concurrent_requests"].setdefault(condition, {"requests": 0,
                            "wall_s": 0, "rounds": [],
                            "note": "Synthetic inference requests, not completed autonomous agent tasks."})
                        result["rounds"].append({"round": round_index, "requests": 3, "wall_s": wall,
                                                "samples": samples})
                        result["requests"] += len(samples)
                        result["wall_s"] += wall
                        result["completed_requests_s"] = result["requests"] / result["wall_s"]
                        result["request_wall_s"] = summarize([x["wall_s"] for x in condition_samples[condition]])
                        checkpoint()
            if embed:
                checkpoint("embeddings")
                preflight_duration = await guard("embeddings")
                corpus = [f"Synthetic document {i}: the robot sorts colored blocks." for i in range(8)]
                payload = {"model": embed["name"], "input": corpus, "keep_alive": "30s"}
                admission_start = time.perf_counter()
                async with dispatcher.lease(embed["name"], host, workload="embeddings") as admission:
                    admission_duration = time.perf_counter() - admission_start
                    payload["keep_alive"] = min(30, admission["keep_alive_s"])
                    payload["options"] = admitted_options({}, admission)
                    http_start = time.perf_counter()
                    response = await client.post(host + "/api/embed", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    vectors = data.get("embeddings") if isinstance(data, dict) else None
                    count = len(vectors) if isinstance(vectors, list) else None
                    dimensions = len(vectors[0]) if count and isinstance(vectors[0], list) else 0
                    vectors_valid = bool(count and dimensions and all(
                        isinstance(vector, list) and len(vector) == dimensions and all(
                            not isinstance(value, bool) and isinstance(value, (int, float))
                            and math.isfinite(value) for value in vector) for vector in vectors))
                    count_pass = count == len(corpus)
                    valid = vectors_valid and count_pass and not data.get("error")
                    duration = data.get("total_duration") if isinstance(data, dict) else None
                    receipt["embeddings"] = {"status": "measured" if valid else "failed",
                        "model": embed["name"], "digest": embed["digest"],
                        "count": count, "dimensions": dimensions, "vectors_valid": vectors_valid,
                        "admission_duration_s": admission_duration,
                        "http_duration_s": time.perf_counter() - http_start,
                        "preflight_duration_s": preflight_duration,
                        "duration_s": duration / 1e9 if not isinstance(duration, bool)
                            and isinstance(duration, (int, float)) and math.isfinite(duration) and duration >= 0 else None,
                        "ordered_count_pass": count_pass,
                        "note": "One bounded batch smoke test; no speedup or quality acceptance."}
                checkpoint()
                if not valid:
                    receipt["halt_reason"] = "embedding_validation_failed"
                    raise RuntimeError("embedding_validation_failed")
            elif "embeddings" in selected:
                receipt["embeddings"] = {"status": "unavailable", "reason": "no_installed_embedding_model"}
            checkpoint("summaries")
            if "llm" in selected:
                for condition, samples in receipt["llm"].items():
                    receipt.setdefault("summaries", {})[condition] = {
                        k: summarize([s[k] for s in samples if s[k] is not None])
                        for k in ("wall_s", "prefill_tokens_s", "decode_tokens_s",
                                  "admission_duration_s", "http_duration_s", "preflight_duration_s")}
        checkpoint("after_snapshot")
        await check_health("after_snapshot", snapshot_key="after")
        return finish("completed", "stock_smoke_benchmarks_complete_not_release_acceptance")
    except BaseException as exc:
        # Exception messages and request/response bodies can contain sensitive text.
        receipt["failures"].append({"exception_type": type(exc).__name__, "stage": receipt["stage"]})
        failure_results = {"matrix_numerical_check_failed": "stock_smoke_benchmarks_failed_matrix_numerical_validation",
                           "embedding_validation_failed": "stock_smoke_benchmarks_failed_embedding_validation"}
        receipt.update(status="cancelled" if isinstance(exc, asyncio.CancelledError) else "failed",
                       result=failure_results.get(receipt.get("halt_reason"),
                                                  "stock_smoke_benchmarks_interrupted_not_release_acceptance"),
                       finished=datetime.now(timezone.utc).isoformat())
        try:
            checkpoint()
        except Exception as save_error:
            # Preserve the original failure and last committed checkpoint if storage fails.
            exc.add_note("Terminal receipt unavailable; checkpoint error type: " + type(save_error).__name__)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, choices=range(3, 11), default=6,
                        help="Paired trials; an even count balances AB/BA condition order (default: 6).")
    parser.add_argument("--model", dest="model_name", help="Exact installed bounded model name; no download.")
    parser.add_argument("--model-digest", help="Require this installed model digest; requires --model.")
    parser.add_argument("--phases", nargs="+", choices=("matrix", "llm", "concurrency", "embeddings"),
                        help="Run only these phases; omitted runs all legacy stock phases.")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.output.resolve(), args.repeats, model_name=args.model_name,
                        model_digest=args.model_digest, phases=args.phases))
    except (Exception, KeyboardInterrupt) as exc:
        print("Benchmark stopped; exception type: " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1) from None
