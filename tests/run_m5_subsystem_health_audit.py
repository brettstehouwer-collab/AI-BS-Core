"""M5 Subsystem Health & Verification Audit.

Verifies all 4 AI-BS subsystems defined in PROJECT.md:
1. Chapter Creator / Native Studio (C++20 DX12 binary, offscreen viewport session, 0 debug errors, nonbackground pixels > 0)
2. FastAPI Master Cognitive Backend (Port 8080 /health, status 'online', GPU accelerated, /api/rag/query, /api/omnidrive/search)
3. ComfyUI RTX 4090 Dual Bridge (Port 8188 primary proxy, Port 8189 high-VRAM proxy, RTX 4090 GPU active with 24GB VRAM)
4. Vite Frontend Build & Dev Environment (Port 5173 dev server HTTP 200, production build 'npm run build' exit code 0, 0 build errors)

Writes structured output to C:\\AI-BS\\tests\\m5_audit_report.json.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = r"C:\AI-BS"
REPORT = os.path.join(ROOT, "tests", "m5_audit_report.json")
EXE = os.path.join(ROOT, r"engine\out\windows-msvc\Debug\aibs_creator_viewport.exe")
VERIFY = os.path.join(ROOT, r"native_studio\verify_sheltered_hub_viewport_session.py")

PACKAGING_PY = r"C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\python.exe"
PYPPETEER_PY = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

NODE_BIN_DIR = r"C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1111-574-0_26.1111.574.0_x64__3k8sg7r9htsxt\dependencies\node\bin"
NPM_SHIMS_DIR = r"C:\Users\Administrator\AppData\Local\OpenAI\Codex\runtimes\cua_node\bbc9141fe9f920ac\bin\node_modules\corepack\shims"


def get_python_exe():
    for p in (PACKAGING_PY, PYPPETEER_PY, sys.executable):
        if os.path.isfile(p):
            return p
    return sys.executable


def is_port_listening(port, host="127.0.0.1", timeout=0.5):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def http(method, url, body=None, timeout=10):
    t0 = time.perf_counter()
    r = {"url": url, "method": method}
    raw = b""
    # Normalise localhost -> 127.0.0.1 if needed for fast connection, but probe url
    probe_url = url
    try:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(probe_url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            r["status_code"] = resp.status
            raw = resp.read(300000)
    except urllib.error.HTTPError as e:
        r["status_code"] = e.code
        raw = e.read(30000) if e.fp else b""
    except Exception as e:
        # Fallback to 127.0.0.1 if localhost encountered error
        if "localhost" in url:
            try:
                fallback_url = url.replace("localhost", "127.0.0.1")
                req = urllib.request.Request(fallback_url, data=data, method=method, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    r["status_code"] = resp.status
                    raw = resp.read(300000)
            except urllib.error.HTTPError as e2:
                r["status_code"] = e2.code
                raw = e2.read(30000) if e2.fp else b""
            except Exception as e2:
                r["status_code"] = None
                r["error"] = f"{type(e2).__name__}: {e2}"
        else:
            r["status_code"] = None
            r["error"] = f"{type(e).__name__}: {e}"
    r["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    text = raw.decode("utf-8", "replace")
    try:
        r["json"] = json.loads(text)
    except Exception:
        r["body_snippet"] = text[:300]
    return r


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            f = find_key(v, key)
            if f is not None:
                return f
    elif isinstance(obj, list):
        for v in obj:
            f = find_key(v, key)
            if f is not None:
                return f
    return None


def ensure_backend():
    """Ensure FastAPI backend is running on port 8080."""
    if is_port_listening(8080):
        return True
    py = PYPPETEER_PY if os.path.isfile(PYPPETEER_PY) else get_python_exe()
    backend_script = os.path.join(ROOT, "backend", "AI_BS_Backend.py")
    subprocess.Popen([py, backend_script], cwd=os.path.join(ROOT, "backend"),
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    for _ in range(30):
        time.sleep(1)
        if is_port_listening(8080):
            return True
    return False


def ensure_comfy():
    """Ensure ComfyUI Dual Bridge proxies are running on ports 8188 & 8189."""
    if is_port_listening(8188) and is_port_listening(8189):
        return True
    py = PYPPETEER_PY if os.path.isfile(PYPPETEER_PY) else get_python_exe()
    proxy_script = os.path.join(ROOT, "backend", "comfy_primary_proxy_8188.py")
    subprocess.Popen([py, proxy_script], cwd=os.path.join(ROOT, "backend"),
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    for _ in range(15):
        time.sleep(1)
        if is_port_listening(8188) and is_port_listening(8189):
            return True
    return False


def ensure_vite():
    """Ensure Vite dev server is running on port 5173."""
    if is_port_listening(5173):
        return True
    frontend_dir = os.path.join(ROOT, "frontend")
    extra_paths = [p for p in (NODE_BIN_DIR, NPM_SHIMS_DIR) if os.path.isdir(p)]
    env = dict(os.environ, PATH=";".join(extra_paths + [os.environ.get("PATH", "")]))
    subprocess.Popen(["cmd.exe", "/c", "npm", "run", "dev"], cwd=frontend_dir, env=env,
                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
    for _ in range(20):
        time.sleep(1)
        if is_port_listening(5173):
            return True
    return False


def audit_native():
    """Subsystem 1: Chapter Creator / Native Studio."""
    res = {"exe_path": EXE, "exe_exists": os.path.isfile(EXE), "failures": []}
    if not res["exe_exists"]:
        res["failures"].append(f"viewport exe missing at {EXE}")

    py = get_python_exe()
    env = dict(os.environ, PYTHONPATH=ROOT)
    t0 = time.perf_counter()
    out = ""
    try:
        p = subprocess.run([py, VERIFY], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        res["exit_code"] = p.returncode
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        res["output_tail"] = out[-2000:]
    except subprocess.TimeoutExpired:
        res["exit_code"] = None
        res["failures"].append("verify script timed out (300s)")
    except Exception as e:
        res["exit_code"] = None
        res["failures"].append(f"verify launch error: {e}")

    res["duration_s"] = round(time.perf_counter() - t0, 2)

    # Read metrics from generated viewport.json on disk if available
    de, nbp = None, None
    vp_json = os.path.join(ROOT, "docs", "viewport_telemetry", "probe_run", "viewport.json")
    if os.path.isfile(vp_json):
        try:
            with open(vp_json, "r", encoding="utf-8") as f:
                vjd = json.load(f)
            de = vjd.get("debug_errors")
            nbp = vjd.get("nonbackground_pixels")
        except Exception:
            pass

    # Regex fallback from stdout
    if de is None:
        m = re.search(r"Debug Errors:\s*(\d+)", out)
        if m:
            de = int(m.group(1))
    if nbp is None:
        m = re.search(r"Non-background Pixels:\s*([0-9,]+)", out)
        if m:
            nbp = int(m.group(1).replace(",", ""))

    # Fallback to JSON line extraction
    if de is None or nbp is None:
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    j = json.loads(line)
                    de = find_key(j, "debug_errors") if de is None else de
                    nbp = find_key(j, "nonbackground_pixels") if nbp is None else nbp
                except Exception:
                    pass

    res["debug_errors"], res["nonbackground_pixels"] = de, nbp
    if res.get("exit_code") != 0:
        res["failures"].append(f"exit code {res.get('exit_code')}")
    if de is None or de != 0:
        res["failures"].append(f"debug_errors={de}")
    if not isinstance(nbp, int) or nbp <= 0:
        res["failures"].append(f"nonbackground_pixels={nbp}")

    res["passed"] = not res["failures"]
    return res


def audit_fastapi():
    """Subsystem 2: FastAPI Master Cognitive Backend."""
    ensure_backend()
    res = {"failures": []}

    # 1. Probe /health
    h = http("GET", "http://localhost:8080/health", timeout=15)
    res["health"] = h
    st = (h.get("json") or {}).get("status") if isinstance(h.get("json"), dict) else None
    if h.get("status_code") != 200 or st != "online":
        res["failures"].append(f"/health code={h.get('status_code')} status={st}")

    gpu = (h.get("json") or {}).get("gpu_accelerated") if isinstance(h.get("json"), dict) else None
    res["gpu_accelerated"] = gpu
    if not gpu:
        res["failures"].append(f"gpu_accelerated={gpu}")

    # 2. Probe /api/rag/query
    rag = http("POST", "http://localhost:8080/api/rag/query",
               {"query": "engineering", "top_k": 3, "collection": "ai_bs_synced_drive_assets"}, timeout=30)
    res["rag_query"] = rag
    if rag.get("status_code") != 200:
        res["failures"].append(f"/api/rag/query code={rag.get('status_code')}")

    # 3. Probe /api/omnidrive/search
    od = http("POST", "http://localhost:8080/api/omnidrive/search",
              {"query": "engineering", "limit": 3}, timeout=30)
    res["omnidrive_search"] = od
    if od.get("status_code") != 200:
        # Fallback probe with GET if POST was unexpected
        od_get = http("GET", "http://localhost:8080/api/omnidrive/search?q=engineering", timeout=30)
        if od_get.get("status_code") == 200:
            res["omnidrive_search"] = od_get
        else:
            res["failures"].append(f"/api/omnidrive/search code={od.get('status_code')}")

    for k in ("rag_query", "omnidrive_search"):
        j = res[k].pop("json", None)
        if j is not None:
            res[k]["json_snippet"] = json.dumps(j)[:500]

    res["passed"] = not res["failures"]
    return res


def audit_comfy():
    """Subsystem 3: ComfyUI RTX 4090 Dual Bridge."""
    ensure_comfy()
    res = {"failures": [], "instances": {}}

    for port in (8188, 8189):
        inst = {}
        for path in ("/health", "/system_stats"):
            inst[path] = http("GET", f"http://localhost:{port}{path}", timeout=10)

        health_resp = inst["/health"]
        stats_resp = inst["/system_stats"]

        if health_resp.get("status_code") != 200:
            res["failures"].append(f"port {port}: /health code={health_resp.get('status_code')}")
        if stats_resp.get("status_code") != 200:
            res["failures"].append(f"port {port}: /system_stats code={stats_resp.get('status_code')}")

        ss = stats_resp.get("json")
        gpu_name = None
        vram_total_gb = None
        vram_free_gb = None

        if isinstance(ss, dict) and ss.get("devices"):
            d = ss["devices"][0]
            gpu_name = d.get("name")
            if d.get("vram_total"):
                vram_total_gb = round(d["vram_total"] / (1024**3), 2)
            if d.get("vram_free"):
                vram_free_gb = round(d["vram_free"] / (1024**3), 2)

        inst["gpu_name"] = gpu_name
        inst["vram_total_gb"] = vram_total_gb
        inst["vram_free_gb"] = vram_free_gb

        if not gpu_name or "RTX 4090" not in gpu_name:
            res["failures"].append(f"port {port}: expected RTX 4090 GPU, got {gpu_name}")
        if vram_total_gb is None or vram_total_gb < 23.0:
            res["failures"].append(f"port {port}: expected 24GB VRAM, got {vram_total_gb}GB")

        inst["passed"] = (health_resp.get("status_code") == 200 and
                          stats_resp.get("status_code") == 200 and
                          gpu_name is not None and "RTX 4090" in gpu_name and
                          vram_total_gb is not None and vram_total_gb >= 23.0)
        res["instances"][str(port)] = inst

    res["passed"] = not res["failures"]
    return res


def audit_vite():
    """Subsystem 4: Vite Frontend Build & Dev Environment."""
    ensure_vite()
    res = {"failures": []}

    # 1. Probe dev server on port 5173
    r = http("GET", "http://localhost:5173/", timeout=10)
    res["dev_server"] = r
    body = (r.get("body_snippet") or "").lower()
    if r.get("status_code") != 200 or ("<!doctype html" not in body and "<html" not in body):
        res["failures"].append(f"dev server code={r.get('status_code')}")

    # 2. Production build check: npm run build in frontend directory
    frontend_dir = os.path.join(ROOT, "frontend")
    extra_paths = [p for p in (NODE_BIN_DIR, NPM_SHIMS_DIR) if os.path.isdir(p)]
    build_env = dict(os.environ, PATH=";".join(extra_paths + [os.environ.get("PATH", "")]))

    t0 = time.perf_counter()
    build_res = {"command": "npm run build"}
    try:
        p = subprocess.run(["cmd.exe", "/c", "npm", "run", "build"],
                           cwd=frontend_dir, env=build_env, capture_output=True, text=True, timeout=120)
        build_res["exit_code"] = p.returncode
        build_out = (p.stdout or "") + "\n" + (p.stderr or "")
        build_res["duration_s"] = round(time.perf_counter() - t0, 2)
        build_res["build_errors"] = 0 if p.returncode == 0 else 1
        if p.returncode != 0:
            res["failures"].append(f"npm run build failed with exit code {p.returncode}")
            build_res["error_tail"] = build_out[-1000:]
    except subprocess.TimeoutExpired:
        build_res["exit_code"] = None
        build_res["build_errors"] = 1
        res["failures"].append("npm run build timed out (120s)")
    except Exception as e:
        build_res["exit_code"] = None
        build_res["build_errors"] = 1
        res["failures"].append(f"npm run build execution error: {e}")

    res["build_check"] = build_res

    # 3. Assert dist/ output
    dist = os.path.join(frontend_dir, "dist", "index.html")
    res["dist_index_exists"] = os.path.isfile(dist)
    if res["dist_index_exists"]:
        res["dist_index_mtime"] = datetime.fromtimestamp(os.path.getmtime(dist)).isoformat()
        assets = os.path.join(frontend_dir, "dist", "assets")
        js_dir = os.path.join(frontend_dir, "dist", "js")
        count = 0
        if os.path.isdir(assets):
            count += len(os.listdir(assets))
        if os.path.isdir(js_dir):
            count += len(os.listdir(js_dir))
        res["dist_asset_count"] = count
    else:
        res["failures"].append("frontend/dist/index.html missing after build")

    res["passed"] = not res["failures"]
    return res


def main():
    report = {
        "audit": "M5 subsystem health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {}
    }

    subsystems = [
        ("native_studio", audit_native),
        ("fastapi", audit_fastapi),
        ("comfyui", audit_comfy),
        ("vite", audit_vite)
    ]

    for name, fn in subsystems:
        try:
            report["subsystems"][name] = fn()
        except Exception as e:
            report["subsystems"][name] = {"passed": False, "failures": [f"audit crashed: {e!r}"]}

    report["overall_passed"] = all(s["passed"] for s in report["subsystems"].values())

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print("=" * 70)
    print("M5 SUBSYSTEM HEALTH AUDIT REPORT")
    print("=" * 70)
    for n, s in report["subsystems"].items():
        status = "PASS" if s["passed"] else "FAIL"
        print(f"[{status}] {n.upper()}")
        if s.get("failures"):
            for f in s["failures"]:
                print(f"       -> {f}")
    print("=" * 70)
    print("OVERALL RESULT:", "PASS" if report["overall_passed"] else "FAIL")
    print("Report written to:", REPORT)
    print("=" * 70)

    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
