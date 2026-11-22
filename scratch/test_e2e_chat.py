import requests
import json
import sys

print("--- Testing /api/v1/hybrid-chat/stream ---")
try:
    r = requests.post(
        "http://127.0.0.1:8080/api/v1/hybrid-chat/stream",
        json={"prompt": "Use your generate_comfy_image tool to create a futuristic neon cyberpunk penthouse overlooking a glowing server matrix", "stream": True},
        stream=True,
        timeout=60
    )
    print("HTTP STATUS:", r.status_code)
    for chunk in r.iter_content(chunk_size=128):
        if chunk:
            sys.stdout.write(chunk.decode('utf-8', errors='ignore'))
            sys.stdout.flush()
    print("\n[HYBRID STREAM DONE]")
except Exception as e:
    print("HYBRID STREAM ERROR:", e)

print("\n--- Testing /api/chat non-streaming fallback ---")
try:
    r = requests.post(
        "http://127.0.0.1:8080/api/chat",
        json={"model": "stehouwer_llm", "messages": [{"role": "user", "content": "Hello"}], "stream": False},
        timeout=60
    )
    print("HTTP STATUS:", r.status_code)
    print("RESPONSE TEXT:", r.text[:200])
except Exception as e:
    print("/api/chat ERROR:", e)
