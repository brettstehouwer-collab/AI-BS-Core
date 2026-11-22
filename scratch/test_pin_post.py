import requests
import urllib3
urllib3.disable_warnings()

s = requests.Session()
s.verify = False
s.auth = ("admin", "admin")

r = s.post("https://localhost:49001/api/pin", json={"pin": "0000"}, timeout=3)
print(f"POST /api/pin -> HTTP {r.status_code}: {r.text}")
