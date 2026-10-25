import os
import sys
import subprocess
import time
import httpx

def start_ollama():
    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if not os.path.exists(ollama_exe):
        print(f"Ollama executable not found at: {ollama_exe}")
        return False

    # CREATE_BREAKAWAY_FROM_JOB (0x01000000) | DETACHED_PROCESS (0x00000008) | CREATE_NO_WINDOW (0x08000000) | CREATE_NEW_PROCESS_GROUP (0x00000200)
    FLAGS = 0x01000000 | 0x00000008 | 0x08000000 | 0x00000200

    # Port 11434
    env1 = os.environ.copy()
    env1["OLLAMA_HOST"] = "127.0.0.1:11434"
    env1["OLLAMA_MODELS"] = r"C:\AI-BS\models\ollama"
    env1["OLLAMA_KEEP_ALIVE"] = "10m"
    env1["OLLAMA_NUM_PARALLEL"] = "4"
    env1["OLLAMA_MAX_LOADED_MODELS"] = "1"
    env1["OLLAMA_FLASH_ATTENTION"] = "1"
    env1["CUDA_VISIBLE_DEVICES"] = "0"
    env1["OLLAMA_IGPU_ENABLE"] = "0"

    p1 = subprocess.Popen(
        [ollama_exe, "serve"],
        env=env1,
        creationflags=FLAGS,
        close_fds=True
    )
    print(f"Spawned Ollama 11434 (PID: {p1.pid})")

    time.sleep(1)

    # Port 11435
    env2 = os.environ.copy()
    env2["OLLAMA_HOST"] = "127.0.0.1:11435"
    env2["OLLAMA_MODELS"] = r"C:\AI-BS\models\ollama"
    env2["OLLAMA_KEEP_ALIVE"] = "10m"
    env2["OLLAMA_NUM_PARALLEL"] = "4"
    env2["OLLAMA_MAX_LOADED_MODELS"] = "1"
    env2["OLLAMA_FLASH_ATTENTION"] = "1"
    env2["CUDA_VISIBLE_DEVICES"] = "0"
    env2["OLLAMA_IGPU_ENABLE"] = "0"

    p2 = subprocess.Popen(
        [ollama_exe, "serve"],
        env=env2,
        creationflags=FLAGS,
        close_fds=True
    )
    print(f"Spawned Ollama 11435 (PID: {p2.pid})")

    time.sleep(3)

    for port in [11434, 11435]:
        for attempt in range(5):
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/api/tags", timeout=5)
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    print(f"Port {port} ACTIVE! Models ({len(models)}): {models}")
                    break
            except Exception as e:
                time.sleep(1)

if __name__ == "__main__":
    start_ollama()
