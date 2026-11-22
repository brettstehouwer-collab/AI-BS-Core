import urllib.request, json
req = urllib.request.Request("http://127.0.0.1:8189/prompt", data=b'{"prompt": {}}', headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req).read().decode())
except Exception as e:
    print("Exception:", e, e.read().decode() if hasattr(e, "read") else "")
