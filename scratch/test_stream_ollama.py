import requests
import json
import sys

payload = {
    "model": "stehouwer_llm",
    "prompt": "Respond in one sentence: Are you online and ready?",
    "stream": True,
    "options": {
        "num_ctx": 4096,
        "temperature": 0.7
    }
}

try:
    r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, stream=True, timeout=60)
    print("HTTP STATUS:", r.status_code)
    for line in r.iter_lines():
        if line:
            chunk = json.loads(line.decode('utf-8'))
            sys.stdout.write(chunk.get("response", ""))
            sys.stdout.flush()
    print("\n[DONE]")
except Exception as e:
    print("ERROR:", e)
