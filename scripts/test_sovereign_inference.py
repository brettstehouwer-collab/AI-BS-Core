"""
Test Sovereign Chat & Ollama Connectivity
"""

import os
import sys
import subprocess
import time
import urllib.request
import json

def check_ollama():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            print(f"[Ollama 11434] Models found: {models}")
            return True
    except Exception as e:
        print(f"[Ollama 11434] Offline: {e}")
        return False

def check_fastapi_chat():
    try:
        payload = json.dumps({
            "model": "stehouwer_llm",
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8080/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            body = resp.read().decode("utf-8")
            print(f"[FastAPI Chat 8080] Response (Status {resp.getcode()}): {body[:200]}")
            return True
    except Exception as e:
        print(f"[FastAPI Chat 8080] Offline / Error: {e}")
        return False

def start_ollama_daemon():
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    env["OLLAMA_MODELS"] = r"E:\AI_BS_Resources\Ollama"
    env["OLLAMA_MAX_LOADED_MODELS"] = "1"
    env["OLLAMA_NUM_PARALLEL"] = "1"
    env["OLLAMA_FLASH_ATTENTION"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["OLLAMA_IGPU_ENABLE"] = "0"
    env["OLLAMA_KEEP_ALIVE"] = "15m"

    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    print(f"Launching {ollama_exe} serve...")
    subprocess.Popen(
        [ollama_exe, "serve"],
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    time.sleep(3)

def main():
    print("=" * 60)
    print("Testing Ollama & FastAPI Chat Endpoint")
    print("=" * 60)
    
    if not check_ollama():
        start_ollama_daemon()
        check_ollama()
        
    check_fastapi_chat()
    print("=" * 60)

if __name__ == "__main__":
    main()
