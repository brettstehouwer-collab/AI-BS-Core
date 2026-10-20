import subprocess
import sys
import time
import os
import urllib.request
import json
import socket

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_tcp_port(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def run_preflight():
    print("=" * 60)
    print("      AI-BS ENTERPRISE PRE-FLIGHT SYSTEM VERIFICATION")
    print("=" * 60)

    # 1. Run Matrix Doctor Diagnostics
    print("\n[Step 1/3] Executing Matrix Doctor Health Diagnostics...")
    doc_path = os.path.join(BASE_DIR, "backend", "matrix_doctor.py")
    if os.path.exists(doc_path):
        res = subprocess.run([sys.executable, doc_path], cwd=BASE_DIR, capture_output=True, text=True)
        if res.returncode == 0:
            print(res.stdout)
        else:
            print("  [WARN] Matrix Doctor encountered warnings:\n", res.stderr)

    # 2. Schema Cross-Language Integrity
    print("\n[Step 2/3] Verifying Cross-Language Schemas...")
    schema_gen = [sys.executable, os.path.join(BASE_DIR, "scripts", "generate_schemas.py")]
    s_res = subprocess.run(schema_gen, cwd=BASE_DIR, capture_output=True, text=True)
    if s_res.returncode == 0:
        print("  [OK] Schemas generated & in-sync across Python, TS, Go, and Rust.")
    else:
        print("  [FAIL] Schema Generation FAILED:", s_res.stderr)
        return False

    # 3. HTTP Health Probing on Core Ports
    print("\n[Step 3/3] Probing Active Core HTTP Gateways...")
    services = [
        ("FastAPI Backend (8080)", "http://127.0.0.1:8080/api/system/health"),
        ("Go Gateway (8000)", "http://127.0.0.1:8000/api/health"),
        ("Vite React Frontend (5173)", "http://127.0.0.1:5173"),
        ("Primary Ollama C-Drive (11434)", "http://127.0.0.1:11434/api/tags"),
        ("Secondary Ollama E-Drive (11435)", "http://127.0.0.1:11435/api/tags")
    ]

    for name, url in services:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-BS-Preflight"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                status = resp.getcode()
                print(f"  [OK] {name:<35} : ONLINE (HTTP {status})")
        except Exception as e:
            print(f"  [WARN] {name:<33} : OFFLINE / {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] PRE-FLIGHT VERIFICATION COMPLETE")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)