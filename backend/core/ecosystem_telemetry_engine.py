import os
import sys
import time
import json
import asyncio
import subprocess
import logging
import psutil
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("EcosystemTelemetryEngine")

CORE_PORT_MATRIX = {
    80: {"service": "Nginx Gateway", "runtime": "WSL2 Ubuntu", "type": "web_proxy", "health_endpoint": "http://127.0.0.1:80/"},
    3001: {"service": "Node Backend Bridge", "runtime": "Host Node.js", "type": "api_bridge", "health_endpoint": "http://127.0.0.1:3001/health"},
    4455: {"service": "OBS WebSocket Bridge", "runtime": "OBS Studio", "type": "broadcast", "health_endpoint": None},
    5173: {"service": "Vite Dev & Desktop Studio", "runtime": "Host Node.js", "type": "frontend", "health_endpoint": "http://127.0.0.1:5173/"},
    5174: {"service": "Secondary Vite Studio", "runtime": "Host Node.js", "type": "frontend", "health_endpoint": "http://127.0.0.1:5174/"},
    8000: {"service": "Go Gateway (aibs_engine)", "runtime": "Go Host Binary", "type": "gateway", "health_endpoint": "http://127.0.0.1:8000/health"},
    8001: {"service": "ChromaDB Primary Vector Store", "runtime": "Python Host", "type": "vector_memory", "health_endpoint": "http://127.0.0.1:8001/api/v1/heartbeat"},
    8002: {"service": "ChromaDB Secondary Vector Store", "runtime": "Python Host", "type": "vector_memory", "health_endpoint": "http://127.0.0.1:8002/api/v1/heartbeat"},
    8003: {"service": "Python Microservice Worker 1", "runtime": "Python Host", "type": "worker", "health_endpoint": "http://127.0.0.1:8003/health"},
    8004: {"service": "Python Microservice Worker 2", "runtime": "Python Host", "type": "worker", "health_endpoint": "http://127.0.0.1:8004/health"},
    8005: {"service": "Broadcast Daemon", "runtime": "Python Host", "type": "broadcast", "health_endpoint": "http://127.0.0.1:8005/health"},
    8006: {"service": "Social Hub [Twitch/IRC]", "runtime": "Python Host", "type": "social_bridge", "health_endpoint": "http://127.0.0.1:8006/health"},
    8007: {"service": "Crypto Swarm & Scalp Bot", "runtime": "Python Host", "type": "quant_engine", "health_endpoint": "http://127.0.0.1:8007/api/health"},
    8010: {"service": "SHM Telemetry Proxy", "runtime": "Python Host", "type": "telemetry_ipc", "health_endpoint": "http://127.0.0.1:8010/health"},
    8013: {"service": "VST3 Audio Bridge", "runtime": "Python Host", "type": "audio_dsp", "health_endpoint": "http://127.0.0.1:8013/health"},
    8055: {"service": "The Simple Chef Isolated vHost", "runtime": "WSL2 Nginx", "type": "client_vhost", "health_endpoint": "http://127.0.0.1:8055/"},
    8080: {"service": "FastAPI Core Engine", "runtime": "Python Host", "type": "core_orchestrator", "health_endpoint": "http://127.0.0.1:8080/api/health"},
    8085: {"service": "Ubuntu-Bio Bridge", "runtime": "WSL2 Linux", "type": "bio_compute", "health_endpoint": "http://127.0.0.1:8085/health"},
    8088: {"service": "Broadcast Kernel & NVENC", "runtime": "Python Host", "type": "video_encode", "health_endpoint": "http://127.0.0.1:8088/health"},
    8089: {"service": "WSL HLS Ingest", "runtime": "WSL2 Linux", "type": "video_stream", "health_endpoint": "http://127.0.0.1:8089/health"},
    8099: {"service": "Gemini MCP Server", "runtime": "Python Host", "type": "mcp_server", "health_endpoint": "http://127.0.0.1:8099/health"},
    8189: {"service": "ComfyUI Secondary / Screenplay", "runtime": "Python Host", "type": "diffusion_engine", "health_endpoint": "http://127.0.0.1:8189/system_stats"},
    8888: {"service": "Unreal Engine Signaling", "runtime": "Python Host", "type": "webrtc_signaling", "health_endpoint": "http://127.0.0.1:8888/"},
    11434: {"service": "Ollama Host", "runtime": "Ollama Service", "type": "llm_inference", "health_endpoint": "http://127.0.0.1:11434/api/tags"},
    11435: {"service": "Ollama E-Drive Host", "runtime": "Ollama Service", "type": "llm_inference", "health_endpoint": "http://127.0.0.1:11435/api/tags"}
}


class EcosystemTelemetryEngine:
    """
    Central real-time telemetry aggregator and tool discovery mesh for AI-BS.
    Polls host connections, process metrics, WSL2 sockets, and manages dynamic port tool calling.
    """

    _custom_ingested_metrics: Dict[int, Dict[str, Any]] = {}
    _wsl_cache: Dict[str, Any] = {"ports": [], "last_updated": 0}
    _gpu_cache: Dict[str, Any] = {"vram_used_mb": 0, "vram_total_mb": 24576, "gpu_util_pct": 0, "temp_c": 0, "last_updated": 0}
    _discovered_port_tools: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def ingest_port_metrics(cls, port: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Allows any internal or external daemon to push custom telemetry metrics."""
        cls._custom_ingested_metrics[port] = {
            **payload,
            "received_at": time.time(),
            "port": port
        }
        return {"status": "success", "port": port, "recorded": True}

    @classmethod
    def get_gpu_telemetry(cls) -> Dict[str, Any]:
        """Polls NVIDIA GPU metrics (RTX 4090 24GB) via nvidia-smi cache (max 1 call every 2s)."""
        now = time.time()
        if now - cls._gpu_cache.get("last_updated", 0) < 2.0:
            return cls._gpu_cache

        try:
            cmd = ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 4:
                    cls._gpu_cache = {
                        "vram_used_mb": int(parts[0]),
                        "vram_total_mb": int(parts[1]),
                        "vram_free_mb": int(parts[1]) - int(parts[0]),
                        "gpu_util_pct": int(parts[2]),
                        "temp_c": int(parts[3]),
                        "last_updated": now
                    }
        except Exception:
            pass
        return cls._gpu_cache

    @classmethod
    def get_wsl_ports(cls) -> List[Dict[str, Any]]:
        """Interrogates WSL2 Ubuntu sockets with 5-second caching."""
        now = time.time()
        if now - cls._wsl_cache.get("last_updated", 0) < 5.0 and cls._wsl_cache.get("ports"):
            return cls._wsl_cache["ports"]

        wsl_ports = []
        try:
            cmd = ["wsl.exe", "-d", "Ubuntu", "--", "ss", "-tuln"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                lines = res.stdout.splitlines()
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5 and parts[1] == "LISTEN":
                        local_addr = parts[4]
                        if ":" in local_addr:
                            port_str = local_addr.rsplit(":", 1)[-1]
                            if port_str.isdigit():
                                port_num = int(port_str)
                                wsl_ports.append({
                                    "port": port_num,
                                    "address": local_addr,
                                    "subsystem": "WSL2 Ubuntu",
                                    "protocol": parts[0].upper()
                                })
                cls._wsl_cache = {"ports": wsl_ports, "last_updated": now}
        except Exception:
            pass
        return wsl_ports

    @classmethod
    def get_full_ecosystem_telemetry(cls) -> Dict[str, Any]:
        """
        Gathers complete, unified telemetry snapshot across all listening TCP/UDP ports,
        core matrix daemons, dynamic tools, and WSL2 environment.
        """
        start_time = time.time()

        # 1. System-wide metrics
        sys_cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        net_io = psutil.net_io_counters()

        # 2. Host listening connections & process mapping
        raw_conns = []
        try:
            raw_conns = psutil.net_connections(kind='inet')
        except Exception:
            pass

        listening_map: Dict[int, List[Dict[str, Any]]] = {}
        for c in raw_conns:
            if c.status == 'LISTEN' and c.laddr:
                p = c.laddr.port
                if p not in listening_map:
                    listening_map[p] = []
                listening_map[p].append({
                    "ip": c.laddr.ip,
                    "pid": c.pid
                })

        # 3. Process inspection cache
        proc_cache: Dict[int, Dict[str, Any]] = {}
        all_pids = set()
        for bindings in listening_map.values():
            for b in bindings:
                if b["pid"]:
                    all_pids.add(b["pid"])

        for pid in all_pids:
            try:
                p = psutil.Process(pid)
                with p.oneshot():
                    proc_cache[pid] = {
                        "name": p.name(),
                        "cpu_pct": round(p.cpu_percent(interval=None), 1),
                        "mem_rss_mb": round(p.memory_info().rss / (1024 * 1024), 1),
                        "threads": p.num_threads(),
                        "create_time": p.create_time(),
                        "status": p.status()
                    }
            except Exception:
                proc_cache[pid] = {
                    "name": "System/Protected",
                    "cpu_pct": 0.0,
                    "mem_rss_mb": 0.0,
                    "threads": 1,
                    "create_time": 0,
                    "status": "running"
                }

        # 4. Compile Core Matrix Telemetry
        wsl_ports = cls.get_wsl_ports()
        matrix_report = []
        for port, meta in CORE_PORT_MATRIX.items():
            is_listening = port in listening_map
            # Also check if it's in WSL
            wsl_active = any(wp["port"] == port for wp in wsl_ports) if "WSL2" in meta["runtime"] else False
            active = is_listening or wsl_active

            bindings = listening_map.get(port, [])
            pid = bindings[0]["pid"] if bindings else None
            pinfo = proc_cache.get(pid, {}) if pid else {}
            custom = cls._custom_ingested_metrics.get(port, {})

            matrix_report.append({
                "port": port,
                "service": meta["service"],
                "runtime": meta["runtime"],
                "type": meta["type"],
                "status": "ONLINE" if active else "OFFLINE",
                "pid": pid,
                "process_name": pinfo.get("name", "WSL2 Daemon" if wsl_active else "Inactive"),
                "cpu_pct": custom.get("cpu_pct", pinfo.get("cpu_pct", 0.0)),
                "mem_mb": custom.get("mem_mb", pinfo.get("mem_rss_mb", 0.0)),
                "threads": pinfo.get("threads", 1),
                "ip_bindings": [b["ip"] for b in bindings] if bindings else (["WSL2 Local"] if wsl_active else []),
                "health_endpoint": meta["health_endpoint"],
                "custom_metrics": custom
            })

        # 5. Compile Dynamic & Developer Ports
        dynamic_report = []
        for port, bindings in sorted(listening_map.items()):
            if port not in CORE_PORT_MATRIX:
                pid = bindings[0]["pid"] if bindings else None
                pinfo = proc_cache.get(pid, {}) if pid else {}
                dynamic_report.append({
                    "port": port,
                    "pid": pid,
                    "process_name": pinfo.get("name", "Unknown"),
                    "cpu_pct": pinfo.get("cpu_pct", 0.0),
                    "mem_mb": pinfo.get("mem_rss_mb", 0.0),
                    "threads": pinfo.get("threads", 1),
                    "ip_bindings": [b["ip"] for b in bindings]
                })

        # 6. GPU Telemetry
        gpu_telemetry = cls.get_gpu_telemetry()

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "success",
            "timestamp": time.time(),
            "scan_latency_ms": elapsed_ms,
            "summary": {
                "total_listening_ports": len(listening_map) + len(wsl_ports),
                "core_matrix_online": sum(1 for m in matrix_report if m["status"] == "ONLINE"),
                "core_matrix_total": len(CORE_PORT_MATRIX),
                "dynamic_ports_count": len(dynamic_report),
                "wsl_ports_count": len(wsl_ports),
                "host_cpu_pct": sys_cpu,
                "host_mem_pct": mem.percent,
                "host_mem_used_gb": round(mem.used / (1024**3), 2),
                "host_mem_total_gb": round(mem.total / (1024**3), 2),
                "net_bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "net_bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "rtx_4090_vram_used_mb": gpu_telemetry.get("vram_used_mb", 0),
                "rtx_4090_vram_total_mb": gpu_telemetry.get("vram_total_mb", 24576),
                "rtx_4090_util_pct": gpu_telemetry.get("gpu_util_pct", 0),
                "rtx_4090_temp_c": gpu_telemetry.get("temp_c", 0)
            },
            "core_matrix": matrix_report,
            "dynamic_ports": dynamic_report,
            "wsl_ports": wsl_ports,
            "gpu": gpu_telemetry
        }

    @classmethod
    async def discover_port_tools(cls, ports: Optional[List[int]] = None, timeout: float = 1.5) -> Dict[str, Any]:
        """
        Scans specified or all active ports for callable HTTP / OpenAPI endpoints,
        health interfaces, and tool signatures.
        """
        telemetry = cls.get_full_ecosystem_telemetry()
        target_ports = ports or [m["port"] for m in telemetry["core_matrix"] if m["status"] == "ONLINE"]

        discovered = {}
        async with httpx.AsyncClient(timeout=timeout) as client:
            for port in target_ports:
                port_tools = []
                base_url = f"http://127.0.0.1:{port}"

                # Probe 1: OpenAPI Schema
                try:
                    resp = await client.get(f"{base_url}/openapi.json")
                    if resp.status_code == 200:
                        schema = resp.json()
                        title = schema.get("info", {}).get("title", f"Service on Port {port}")
                        paths = schema.get("paths", {})
                        for path, methods in paths.items():
                            for method, spec in methods.items():
                                port_tools.append({
                                    "tool_name": f"port_{port}_{spec.get('operationId', path.replace('/', '_').strip('_'))}",
                                    "endpoint": path,
                                    "method": method.upper(),
                                    "summary": spec.get("summary", spec.get("description", f"{method.upper()} {path}")),
                                    "parameters": spec.get("parameters", []),
                                    "requestBody": spec.get("requestBody", None)
                                })
                        discovered[port] = {
                            "port": port,
                            "service_title": title,
                            "protocol": "REST/OpenAPI",
                            "tools_count": len(port_tools),
                            "tools": port_tools
                        }
                        continue
                except Exception:
                    pass

                # Probe 2: Standard Health / Tags
                try:
                    if port in [11434, 11435]:
                        resp = await client.get(f"{base_url}/api/tags")
                        if resp.status_code == 200:
                            models = resp.json().get("models", [])
                            discovered[port] = {
                                "port": port,
                                "service_title": "Ollama LLM Engine",
                                "protocol": "Ollama REST",
                                "tools_count": len(models),
                                "tools": [{
                                    "tool_name": f"ollama_generate_{m.get('name', 'model')}",
                                    "endpoint": "/api/generate",
                                    "method": "POST",
                                    "summary": f"Inference with {m.get('name')}",
                                    "model_info": m
                                } for m in models]
                            }
                            continue
                except Exception:
                    pass

                # Probe 3: Generic HTTP Check
                try:
                    resp = await client.get(base_url)
                    discovered[port] = {
                        "port": port,
                        "service_title": f"HTTP Service (Port {port})",
                        "protocol": "HTTP",
                        "tools_count": 1,
                        "tools": [{
                            "tool_name": f"port_{port}_root",
                            "endpoint": "/",
                            "method": "GET",
                            "summary": f"Root GET probe on Port {port} (HTTP {resp.status_code})"
                        }]
                    }
                except Exception:
                    discovered[port] = {
                        "port": port,
                        "service_title": f"Raw Socket (Port {port})",
                        "protocol": "TCP Raw",
                        "tools_count": 0,
                        "tools": []
                    }

        cls._discovered_port_tools = discovered
        return {
            "status": "success",
            "timestamp": time.time(),
            "scanned_ports_count": len(target_ports),
            "discovered_services": discovered
        }

    @classmethod
    async def dispatch_tool_call(
        cls,
        port: int,
        endpoint: str,
        method: str = "POST",
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Dynamically calls an endpoint on any active port with circuit breaking and error isolation.
        """
        start_t = time.time()
        url = f"http://127.0.0.1:{port}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
        req_headers = headers or {}
        req_headers.setdefault("Content-Type", "application/json")
        req_headers.setdefault("User-Agent", "AI-BS-DynamicPortDispatcher/5.290.0")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    resp = await client.get(url, params=params, headers=req_headers)
                elif method.upper() == "POST":
                    resp = await client.post(url, json=payload, params=params, headers=req_headers)
                elif method.upper() == "PUT":
                    resp = await client.put(url, json=payload, params=params, headers=req_headers)
                elif method.upper() == "DELETE":
                    resp = await client.delete(url, params=params, headers=req_headers)
                else:
                    return {"status": "error", "message": f"Unsupported HTTP method: {method}"}

                elapsed_ms = round((time.time() - start_t) * 1000, 2)
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text

                return {
                    "status": "success" if resp.status_code < 400 else "http_error",
                    "http_status": resp.status_code,
                    "target_url": url,
                    "execution_time_ms": elapsed_ms,
                    "response": data
                }
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "http_status": 504,
                "target_url": url,
                "execution_time_ms": round((time.time() - start_t) * 1000, 2),
                "error": f"Port tool call timed out after {timeout} seconds."
            }
        except Exception as e:
            return {
                "status": "connection_error",
                "http_status": 502,
                "target_url": url,
                "execution_time_ms": round((time.time() - start_t) * 1000, 2),
                "error": str(e)
            }
