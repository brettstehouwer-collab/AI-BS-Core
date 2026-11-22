"""Advisory precision capability selection, never firmware/kernel activation."""
from __future__ import annotations


def precision_recommendation(workload: str, *, backend: str = "ollama", supported: tuple[str, ...] = (),
                             requested: str | None = None, model_quantization: str | None = None) -> dict:
    if backend == "ollama":
        return {"backend": backend, "precision": "backend_managed", "model_quantization": model_quantization,
                "changed": False, "tensor_core_use_verified": False,
                "reason": "Ollama model quantization and kernels require backend evidence; no dtype override sent."}
    allowed = tuple(value for value in supported if value in ("fp32", "tf32", "fp16", "bf16", "int8", "int4"))
    if requested is not None and requested not in allowed:
        raise ValueError("unsupported_precision")
    selected = requested or next((value for value in ("bf16", "fp16", "fp32") if value in allowed), None)
    return {"backend": backend, "precision": selected, "supported": list(allowed), "changed": False,
            "tensor_core_use_verified": False, "workload": workload,
            "reason": "Recommendation only; caller must validate numerical tolerance and actual kernel support."}
