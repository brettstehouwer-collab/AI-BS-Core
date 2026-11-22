"""Dear PyGui live-telemetry HUD (separate native process, DirectX 11 immediate-mode GUI).

Launched by the Studio (``launch_hud()``) or standalone:

    python native_studio/dpg_hud.py

Reads the shared-memory telemetry frame written by ``TelemetryHub``. There are no
sockets and no web runtime. Qt and Dear PyGui each want to own the main-thread event
loop, so they live in two processes joined by RAM, not by the network.
"""

from __future__ import annotations

import subprocess
import sys
import time
from collections import deque
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from native_studio.telemetry_shm import HISTORY, PORT_ORDER, TelemetryReader  # noqa: E402

SERIES = {
    "gpu_temp_c": "GPU temp C", "gpu_util_pct": "GPU util %", "gpu_power_w": "GPU power W",
    "gpu_vram_used_gb": "VRAM used GB", "cpu_pct": "CPU %", "ram_pct": "RAM %",
    "aud_cb_avg_ms": "audio cb avg ms", "aud_cb_max_ms": "audio cb max ms", "aud_block_ms": "audio block budget ms",
    "ai_step_ms": "AI step ms", "ai_gflops": "AI GFLOPS", "ai_loss": "AI loss",
}


def launch_hud() -> subprocess.Popen:
    """Start the HUD as a detached native process (no console window)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = [sys.executable, "--hud"] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
    return subprocess.Popen(cmd, creationflags=flags)


def main() -> int:
    import dearpygui.dearpygui as dpg

    reader = None
    hist = {k: deque([0.0] * HISTORY, maxlen=HISTORY) for k in SERIES}
    xs = list(range(HISTORY))
    active_ports = [(i, port, label) for i, (port, label) in enumerate(PORT_ORDER) if port != 4455]

    dpg.create_context()
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (7, 11, 20))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (13, 20, 36))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (18, 27, 48))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (30, 42, 68))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 237, 247))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (7, 11, 20), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, (13, 20, 36), category=dpg.mvThemeCat_Plots)
    with dpg.theme() as on_t, dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (52, 211, 153, 120))
    with dpg.theme() as off_t, dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (251, 113, 133, 90))

    def plot(tag: str, title: str, keys: list[str], height: int = 150) -> None:
        with dpg.plot(label=title, height=height, width=-1, no_mouse_pos=True):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True, tag=f"{tag}_x")
            with dpg.plot_axis(dpg.mvYAxis, tag=f"{tag}_y"):
                for k in keys:
                    dpg.add_line_series(xs, list(hist[k]), label=SERIES[k], tag=f"s_{k}")

    with dpg.window(tag="main", no_title_bar=True, no_move=True, no_resize=True):
        dpg.add_text("AI-BS NATIVE TELEMETRY HUD  |  Dear PyGui / DirectX 11  |  RAM-only IPC", color=(34, 211, 238))
        dpg.add_text("waiting for Studio telemetry...", tag="status", color=(139, 155, 180))
        dpg.add_separator()
        with dpg.group(horizontal=True):
            with dpg.child_window(width=470, height=-1):
                dpg.add_text("GPU  RTX 4090 (NVML)", color=(167, 139, 250))
                dpg.add_text("--", tag="gpu_line")
                dpg.add_progress_bar(tag="vram_bar", width=-1, overlay="VRAM")
                dpg.add_text("--", tag="compute_line")
                dpg.add_separator()
                dpg.add_text("HOST", color=(167, 139, 250))
                dpg.add_text("--", tag="host_line")
                dpg.add_separator()
                dpg.add_text("AUDIO KERNEL", color=(167, 139, 250))
                dpg.add_text("--", tag="aud_line")
                dpg.add_text("--", tag="aud_line2")
                dpg.add_separator()
                dpg.add_text("AI COMPUTE WORKER", color=(167, 139, 250))
                dpg.add_text("--", tag="ai_line")
                dpg.add_separator()
                dpg.add_text(f"{len(active_ports)}-PORT COLLISION MATRIX", color=(167, 139, 250))
                for offset in range(0, len(active_ports), 4):
                    with dpg.group(horizontal=True):
                        for i, port, label in active_ports[offset:offset + 4]:
                            dpg.add_button(label=f"{port}\n{label}", width=108, height=44,
                                           tag=f"port_{i}")
            with dpg.child_window(width=-1, height=-1):
                plot("gpu", "GPU thermals / load", ["gpu_temp_c", "gpu_util_pct", "gpu_power_w"])
                plot("mem", "Memory", ["gpu_vram_used_gb", "ram_pct", "cpu_pct"])
                plot("aud", "Audio callback (ms) vs block budget", ["aud_cb_avg_ms", "aud_cb_max_ms", "aud_block_ms"])
                plot("ai", "AI worker", ["ai_step_ms", "ai_gflops", "ai_loss"])

    dpg.bind_theme(theme)
    dpg.create_viewport(title="AI-BS Native Telemetry HUD", width=1360, height=900, vsync=True)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main", True)
    dpg.show_viewport()

    last_poll = 0.0
    while dpg.is_dearpygui_running():
        now = time.time()
        if now - last_poll >= 0.25:
            last_poll = now
            if reader is None:
                try:
                    reader = TelemetryReader()
                except FileNotFoundError:
                    dpg.set_value("status", "waiting for Studio telemetry (start AI-BS Studio)...")
            if reader is not None:
                f = reader.read()
                age = now - f["ts"] if f["ts"] else 1e9
                dpg.set_value("status", f"LIVE  frame #{int(f['seq'] // 2)}  age {age * 1000:.0f} ms"
                              if age < 3 else f"STALE (Studio not publishing, {age:.0f}s)")
                for k in SERIES:
                    hist[k].append(f[k])
                    dpg.set_value(f"s_{k}", [xs, list(hist[k])])
                for p in ("gpu", "mem", "aud", "ai"):
                    dpg.fit_axis_data(f"{p}_x")
                    dpg.fit_axis_data(f"{p}_y")
                if f["gpu_ok"]:
                    dpg.set_value("gpu_line", f"{f['gpu_temp_c']:.0f} C | util {f['gpu_util_pct']:.0f}% | "
                                              f"{f['gpu_power_w']:.0f}/{f['gpu_power_limit_w']:.0f} W | fan {f['gpu_fan_pct']:.0f}% | "
                                              f"{f['gpu_core_mhz']:.0f}/{f['gpu_mem_mhz']:.0f} MHz")
                    tot = max(f["gpu_vram_total_gb"], 1e-6)
                    dpg.set_value("vram_bar", f["gpu_vram_used_gb"] / tot)
                    dpg.configure_item("vram_bar", overlay=f"VRAM {f['gpu_vram_used_gb']:.1f}/{tot:.0f} GB")
                else:
                    dpg.set_value("gpu_line", "NVML not available")
                node = "CPU node :11435 (VRAM pressure)" if f["compute_target"] >= 1 else "GPU node :11434"
                dpg.set_value("compute_line", f"VRAM governor routes inference to: {node} | models loaded {f['ollama_loaded']:.0f}")
                dpg.set_value("host_line", f"CPU {f['cpu_pct']:.0f}% | RAM {f['ram_used_gb']:.1f}/{f['ram_total_gb']:.0f} GB ({f['ram_pct']:.0f}%)")
                if f["aud_running"]:
                    mode = "WASAPI EXCLUSIVE" if f["aud_exclusive"] else "WASAPI shared (fallback)"
                    dpg.set_value("aud_line", f"{mode} | reported latency {f['aud_latency_ms']:.2f} ms | block {f['aud_block_ms']:.2f} ms")
                    dpg.set_value("aud_line2", f"callback avg {f['aud_cb_avg_ms']:.3f} / max {f['aud_cb_max_ms']:.3f} ms | "
                                               f"load {f['aud_cpu_pct']:.1f}% | underflows {f['aud_underflows']:.0f} | {f['aud_bpm']:.0f} BPM")
                else:
                    dpg.set_value("aud_line", "engine stopped")
                    dpg.set_value("aud_line2", "")
                if f["ai_running"]:
                    dev = "CUDA" if f["ai_cuda"] else "CPU"
                    dpg.set_value("ai_line", f"{dev} | iter {f['ai_iter']:.0f} | {f['ai_step_ms']:.2f} ms/step | "
                                             f"{f['ai_gflops']:.1f} GFLOPS | loss {f['ai_loss']:.4f}")
                else:
                    dpg.set_value("ai_line", "idle")
                mask = int(f["ports_mask"])
                for i, _, _ in active_ports:
                    dpg.bind_item_theme(f"port_{i}", on_t if (mask >> i) & 1 else off_t)
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
    if reader:
        reader.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
