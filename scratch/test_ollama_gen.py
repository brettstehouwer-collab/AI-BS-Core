import requests
import json

try:
    r = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "stehouwer_llm", "prompt": "Hello, are you online?", "stream": False},
        timeout=60
    )
    print("STATUS:", r.status_code)
    data = r.json()
    print("RESPONSE:", data.get("response"))
except Exception as e:
    print("ERROR:", e)
