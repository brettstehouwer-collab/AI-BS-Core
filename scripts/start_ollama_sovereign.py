import os
import sys
import subprocess
import time
import socket
import urllib.request
import json

def is_port_listening(port: int) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        res = s.connect_ex(("127.0.0.1", port))
        s.close()
        return res == 0
    except Exception:
        return False

def spawn_ollama_instance(port: int, ollama_exe: str):
    if is_port_listening(port):
        print(f"[Ollama Launcher] Port {port} is already listening. Skipping spawn.")
        return None

    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"0.0.0.0:{port}"
    env["OLLAMA_MODELS"] = r"C:\AI-BS\models\ollama"

    if port == 11435:
        # PURE-CPU Workhorse on AMD Ryzen 9 9950X (32 Threads, AVX-512)
        # Dedicated to background embeddings, ChromaDB indexing, and non-blocking audits (0 VRAM)
        env["CUDA_VISIBLE_DEVICES"] = "-1"
        env["OLLAMA_LLM_LIBRARY"] = "cpu"
        env["OLLAMA_NUM_PARALLEL"] = "4"
        env["OLLAMA_MAX_LOADED_MODELS"] = "2"
        env["OLLAMA_FLASH_ATTENTION"] = "0"
        env["OLLAMA_KEEP_ALIVE"] = "60m"
        print(f"[Ollama Launcher] Configuring Port {port} as PURE-CPU Node (Ryzen 9 9950X AVX-512, 0 VRAM)...")
    else:
        # DEDICATED RTX 4090 GPU Node (Port 11434)
        # Handles low-latency chat, code generation, and sovereign reasoning
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["OLLAMA_MAX_LOADED_MODELS"] = "1"
        env["OLLAMA_NUM_PARALLEL"] = "1"
        env["OLLAMA_FLASH_ATTENTION"] = "1"
        env["OLLAMA_KEEP_ALIVE"] = "5m"
        print(f"[Ollama Launcher] Configuring Port {port} as DEDICATED GPU Node (RTX 4090 24GB)...")

    # CREATE_NO_WINDOW (0x08000000) | CREATE_NEW_PROCESS_GROUP (0x00000200) | DETACHED_PROCESS (0x00000008)
    creation_flags = 0x08000000 | 0x00000200 | 0x00000008

    print(f"[Ollama Launcher] Spawning Ollama on port {port}...")
    proc = subprocess.Popen(
        [ollama_exe, "serve"],
        env=env,
        creationflags=creation_flags,
        close_fds=True
    )
    print(f"[Ollama Launcher] Ollama port {port} spawned with PID: {proc.pid}")
    return proc

def start_ollama():
    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if not os.path.exists(ollama_exe):
        print(f"[Ollama Launcher] Ollama binary not found at {ollama_exe}")
        sys.exit(1)

    procs = {}
    p1 = spawn_ollama_instance(11434, ollama_exe)
    if p1: procs[11434] = p1
    time.sleep(1)
    p2 = spawn_ollama_instance(11435, ollama_exe)
    if p2: procs[11435] = p2
    time.sleep(2)

    for port in [11434, 11435]:
        for attempt in range(5):
            try:
                res = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/tags", timeout=3)
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    print(f"[Ollama Launcher] Port {port} ONLINE ({len(models)} models available)")
                    break
            except Exception as e:
                time.sleep(1)

    # Supervisor loop: keep alive and maintain process tree
    try:
        while True:
            time.sleep(60)
            for port in [11434, 11435]:
                if not is_port_listening(port):
                    print(f"[Ollama Supervisor] Port {port} lost connection. Respawning...")
                    p = spawn_ollama_instance(port, ollama_exe)
                    if p: procs[port] = p
    except (KeyboardInterrupt, SystemExit):
        for port, p in procs.items():
            try: p.terminate()
            except Exception: pass

if __name__ == "__main__":
    start_ollama()
