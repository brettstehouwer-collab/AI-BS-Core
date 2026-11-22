import requests
import urllib3
urllib3.disable_warnings()

s = requests.Session()
s.verify = False
s.auth = ("admin", "admin")

try:
    r = s.get("https://localhost:49001/api/pin", timeout=2)
    print(f"GET /api/pin -> HTTP {r.status_code}: {r.text}")
except Exception as e:
    print(f"Error: {e}")
