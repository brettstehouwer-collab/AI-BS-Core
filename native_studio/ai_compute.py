"""Background AI/CUDA compute worker for the Native Studio.

``AiComputeWorker`` is a ``QThread`` that owns every tensor operation. The GUI
thread never touches torch; results travel back as queued Qt signals, so there
is no web server, no HTTP and no WebSocket between the UI and the compute.

Jobs are plain generator functions ``job(ctx) -> Iterator[dict]`` that yield a
metrics dict per iteration. Two jobs ship in the box:

* ``reference_training_job``  - autograd/AdamW MLP loop. Works on CUDA when the
  installed torch build has it, otherwise on CPU. The device actually used is
  always reported (``cuda`` in the metrics) - never assumed.
* ``ollama_stream_job``       - streams tokens from the local Ollama daemon
  (port chosen by the VRAM governor: 11434 GPU node, 11435 CPU node).

Write your own job and pass it to ``AiComputeWorker(job)`` to drive any model
(ONNX Runtime DirectML, llama.cpp, diffusion...) with the same UI plumbing.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from PyQt6.QtCore import QThread, pyqtSignal


@dataclass
class JobContext:
    stop: threading.Event
    log: Callable[[str], None]
    params: dict[str, Any] = field(default_factory=dict)


def torch_device_info() -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        return {"torch": False, "cuda": False, "error": str(exc)}
    cuda = bool(torch.cuda.is_available())
    return {"torch": True, "version": torch.__version__, "cuda": cuda,
            "device": torch.cuda.get_device_name(0) if cuda else "CPU (torch build has no CUDA)"}


def reference_training_job(ctx: JobContext) -> Iterator[dict[str, Any]]:
    import torch
    import torch.nn as nn

    cuda = torch.cuda.is_available()
    dev = torch.device("cuda" if cuda else "cpu")
    if not cuda:
        torch.set_num_threads(max(1, (os.cpu_count() or 8) // 4))  # leave cores for audio + UI
    width = int(ctx.params.get("width", 1024 if cuda else 256))
    batch = int(ctx.params.get("batch", 2048 if cuda else 256))
    d_in = 64
    model = nn.Sequential(nn.Linear(d_in, width), nn.GELU(), nn.Linear(width, width), nn.GELU(),
                          nn.Linear(width, 1)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3)
    n_params = sum(p.numel() for p in model.parameters())
    flops_per_step = 6.0 * n_params * batch  # fwd + bwd approximation
    ctx.log(f"reference job on {dev} | params={n_params:,} batch={batch}")
    it = 0
    while not ctx.stop.is_set():
        x = torch.randn(batch, d_in, device=dev)
        y = torch.sin(x[:, :8]).sum(dim=1, keepdim=True)
        if cuda:
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        opt.zero_grad(set_to_none=True)
        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()
        opt.step()
        if cuda:
            torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        it += 1
        yield {
            "iter": it, "step_ms": dt * 1000.0, "gflops": flops_per_step / dt / 1e9,
            "loss": float(loss.item()), "cuda": cuda,
            "vram_mb": torch.cuda.memory_allocated() / 1048576 if cuda else 0.0,
        }
        if not cuda:
            time.sleep(0.02)  # cooperative: keep the CPU fallback polite


def ollama_stream_job(ctx: JobContext) -> Iterator[dict[str, Any]]:
    import httpx

    port = int(ctx.params.get("port", 11434))
    model = ctx.params.get("model", "stehouwer-hermes:latest")
    prompt = ctx.params.get("prompt", "Say hello from the native studio.")
    ctx.log(f"ollama stream -> :{port} {model}")
    t0, n = time.perf_counter(), 0
    try:
        with httpx.Client(timeout=httpx.Timeout(300.0, connect=2.0)) as client:
            with client.stream("POST", f"http://127.0.0.1:{port}/api/generate",
                               json={"model": model, "prompt": prompt, "stream": True, "keep_alive": 0}) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if ctx.stop.is_set():
                        break
                    if not line:
                        continue
                    chunk = json.loads(line)
                    tok = chunk.get("response", "")
                    if tok:
                        n += 1
                        yield {"iter": n, "token": tok, "cuda": port == 11434,
                               "step_ms": 0.0, "gflops": 0.0, "loss": 0.0, "vram_mb": 0.0,
                               "tok_s": n / max(1e-6, time.perf_counter() - t0)}
                    if chunk.get("done"):
                        break
    finally:
        try:
            with httpx.Client(timeout=2.0) as evict_c:
                evict_c.post(f"http://127.0.0.1:{port}/api/generate", json={"model": model, "keep_alive": 0})
        except Exception:
            pass


class AiComputeWorker(QThread):
    metrics = pyqtSignal(dict)   # one dict per job iteration (throttled)
    log = pyqtSignal(str)
    state = pyqtSignal(str)      # "running" | "stopped" | "error: ..."

    def __init__(self, job: Callable[[JobContext], Iterator[dict[str, Any]]] = reference_training_job,
                 params: dict[str, Any] | None = None, max_hz: float = 20.0, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.job, self.params, self.max_hz = job, params or {}, max_hz
        self._stop = threading.Event()
        self.last: dict[str, Any] = {}

    def request_stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        self.setPriority(QThread.Priority.LowPriority)  # never compete with the audio thread
        self._stop.clear()
        self.state.emit("running")
        ctx = JobContext(self._stop, self.log.emit, self.params)
        min_dt, last_emit = 1.0 / self.max_hz, 0.0
        try:
            for m in self.job(ctx):
                self.last = m
                now = time.perf_counter()
                if now - last_emit >= min_dt:
                    last_emit = now
                    self.metrics.emit(m)
                if self._stop.is_set():
                    break
            self.state.emit("stopped")
        except Exception as exc:  # noqa: BLE001
            self.state.emit(f"error: {type(exc).__name__}: {exc}")
        finally:
            self.last = {}
