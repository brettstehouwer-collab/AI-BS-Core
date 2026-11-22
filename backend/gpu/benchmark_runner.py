"""Small reproducible benchmark records; never applies firmware or GPU settings."""
import hashlib
import math
import statistics


def summarize(samples):
    values = sorted(float(v) for v in samples)
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("finite nonnegative samples required")
    def percentile(p):
        index = (len(values) - 1) * p
        lo, hi = math.floor(index), math.ceil(index)
        return values[lo] + (values[hi] - values[lo]) * (index - lo)
    return {"n": len(values), "median": statistics.median(values),
            "min": values[0], "max": values[-1], "p95": percentile(.95), "p99": percentile(.99)}


def ollama_metrics(data, wall_s):
    if not isinstance(data, dict):
        raise ValueError("invalid_ollama_metrics")
    if isinstance(wall_s, bool) or not isinstance(wall_s, (int, float)) or not math.isfinite(wall_s) or wall_s < 0:
        raise ValueError("invalid_wall_duration")
    response = data.get("response", "")
    if not isinstance(response, str):
        raise ValueError("invalid_ollama_response")
    def observed_number(key):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return None
        return value
    def rate(count, duration):
        c, d = observed_number(count), observed_number(duration)
        if c is None or d is None or d <= 0:
            return None
        result = c / d * 1e9
        return result if math.isfinite(result) else None
    load = observed_number("load_duration")
    cached = observed_number("prompt_eval_cached_count")
    return {"wall_s": wall_s, "load_s": load / 1e9 if load is not None else None,
            "prefill_tokens": observed_number("prompt_eval_count"), "cached_tokens": cached,
            "prefill_tokens_s": rate("prompt_eval_count", "prompt_eval_duration"),
            "decode_tokens": observed_number("eval_count"), "decode_tokens_s": rate("eval_count", "eval_duration"),
            "output_sha256": hashlib.sha256(response.encode()).hexdigest(),
            "prefill_caveat": "reported token count may include cached tokens; no uncached-prefill claim"}


def cuda_matrix_benchmark(size=2048, repeats=5, inner=20):
    """Use CUDA events after warmup; numerical comparison uses an FP32 reference."""
    import torch
    if not torch.cuda.is_available():
        return {"status": "unavailable", "reason": "cuda_not_available"}
    if not 128 <= size <= 4096 or not 3 <= repeats <= 20 or not 1 <= inner <= 50:
        raise ValueError("benchmark bounds exceeded")
    results = {"status": "measured", "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
               "size": size, "warmup": 5, "repeats": repeats, "inner": inner,
               "precision_note": "cuBLAS GEMM, no instruction throughput or Tensor Core unlock attribution", "dtypes": {}}
    previous_tf32 = torch.backends.cuda.matmul.allow_tf32
    torch.backends.cuda.matmul.allow_tf32 = False
    try:
        for label, dtype in (("fp16", torch.float16), ("bf16", torch.bfloat16)):
            if label == "bf16" and not torch.cuda.is_bf16_supported():
                results["dtypes"][label] = {"status": "unsupported"}
                continue
            generator = torch.Generator(device="cuda").manual_seed(42)
            a = torch.randn(size, size, device="cuda", dtype=dtype, generator=generator)
            b = torch.randn(size, size, device="cuda", dtype=dtype, generator=generator)
            output = torch.empty_like(a)
            for _ in range(5):
                torch.mm(a, b, out=output)
            torch.cuda.synchronize()
            timings = []
            for _ in range(repeats):
                start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
                start.record()
                for _ in range(inner):
                    torch.mm(a, b, out=output)
                end.record()
                end.synchronize()
                timings.append(start.elapsed_time(end) / inner)
            # Quantized inputs compared in FP32; test arithmetic, not model quality.
            ref = a[:256, :256].float() @ b[:256, :256].float()
            actual = (a[:256, :256] @ b[:256, :256]).float()
            error = float(torch.linalg.vector_norm(actual - ref) / torch.linalg.vector_norm(ref))
            tolerance = .002 if label == "fp16" else .02
            results["dtypes"][label] = {"status": "measured", "ms": summarize(timings),
                "tflops": summarize([2 * size ** 3 / (ms / 1000) / 1e12 for ms in timings]),
                "relative_l2_error": error, "tolerance": tolerance, "numerical_pass": error <= tolerance}
            del a, b, output, ref, actual
    finally:
        torch.backends.cuda.matmul.allow_tf32 = previous_tf32
    return results
