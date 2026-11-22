import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=json.dumps({"model": "stehouwer_llm:latest", "prompt": "Say PONG", "stream": False}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=15) as res:
    data = json.loads(res.read().decode('utf-8'))
    print("OLLAMA INFERENCE SUCCESS:", data.get('response', ''))

