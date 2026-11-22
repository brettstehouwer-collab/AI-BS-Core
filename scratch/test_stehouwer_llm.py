import json
import urllib.request
import time

def query_ollama(prompt, system_override=None):
    payload = {
        "model": "stehouwer_llm",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    if system_override:
        payload["system"] = system_override
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            return res.get("response", ""), elapsed
    except Exception as e:
        return f"Error: {e}", 0

print("=== TEST 1: Identity & Persona ===")
resp1, t1 = query_ollama("Who are you, what system do you govern, and who is your operator?")
print(f"Time: {t1:.2f}s\nResponse:\n{resp1}\n")

print("=== TEST 2: High-Precision Coding (FIM / AST Refactor) ===")
code_prompt = "Write a complete, production-ready Python FastAPI background worker that handles async email synchronization with error handling and retry logic. No placeholders."
resp2, t2 = query_ollama(code_prompt)
print(f"Time: {t2:.2f}s\nResponse:\n{resp2[:600]}...\n")

print("=== TEST 3: Sovereign Tool Orchestration ===")
tool_prompt = "Inspect the live status of the email daemon and sync the inbox for user brett@stehouwer.ai."
resp3, t3 = query_ollama(tool_prompt)
print(f"Time: {t3:.2f}s\nResponse:\n{resp3}\n")
