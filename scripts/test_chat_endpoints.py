import urllib.request
import json
import time

print("=" * 70)
print("            BS-CHAT ENDPOINT & STREAMING TEST HARNESS")
print("=" * 70)

# 1. Test Ollama Model Availability (Port 11434)
print("\n[1] LOCAL OLLAMA MODELS PROBE (Port 11434)")
try:
    req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        models = [m['name'] for m in data.get('models', [])]
        print(f"  Available Ollama Models ({len(models)}): {', '.join(models[:6])}")
except Exception as e:
    print(f"  Ollama Probe Error: {e}")

# 2. Test FastAPI Standard Chat Endpoint (/api/chat on Port 8080)
print("\n[2] FASTAPI STANDARD CHAT ENDPOINT (/api/chat on Port 8080)")
try:
    payload = {
        "messages": [{"role": "user", "content": "ping"}],
        "model": "stehouwer_llm",
        "temperature": 0.3
    }
    req = urllib.request.Request(
        'http://127.0.0.1:8080/api/chat',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
            'X-Client-ID': 'stehouwer_publishing'
        }
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        elapsed = round((time.time() - t0) * 1000, 1)
        res_data = json.loads(resp.read().decode('utf-8'))
        content = res_data.get('response') or res_data.get('choices', [{}])[0].get('message', {}).get('content') or str(res_data)
        print(f"  [PASS] /api/chat responded in {elapsed}ms -> {str(content)[:70]}...")
except Exception as e:
    print(f"  [WARN] /api/chat error: {e}")

# 3. Test Hybrid Streaming Chat Endpoint (/api/v1/hybrid-chat/stream on Port 8080)
print("\n[3] HYBRID REASONING STREAMING CHAT (/api/v1/hybrid-chat/stream on Port 8080)")
try:
    payload = {
        "prompt": "Hello BS-Studio",
        "stream": True
    }
    req = urllib.request.Request(
        'http://127.0.0.1:8080/api/v1/hybrid-chat/stream',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
            'X-Client-ID': 'stehouwer_publishing'
        }
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        first_chunk = resp.read(64).decode('utf-8', errors='ignore')
        elapsed = round((time.time() - t0) * 1000, 1)
        print(f"  [PASS] /api/v1/hybrid-chat/stream first token in {elapsed}ms -> '{first_chunk[:45]}'")
except Exception as e:
    print(f"  [WARN] /api/v1/hybrid-chat/stream error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETED.")
print("=" * 70)
