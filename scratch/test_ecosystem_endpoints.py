import urllib.request
import json

tests = [
    'http://127.0.0.1:8000/api/health',
    'http://127.0.0.1:8000/health',
    'http://127.0.0.1:8000/api/models',
    'http://127.0.0.1:8013/api/vst/theme-state',
    'http://127.0.0.1:8080/health',
    'http://127.0.0.1:5173/'
]

for url in tests:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AI-BS-Validator'})
        with urllib.request.urlopen(req, timeout=3) as res:
            code = res.getcode()
            print(f"[PASS] {url} -> HTTP {code}")
    except Exception as ex:
        print(f"[FAIL] {url} -> {ex}")
