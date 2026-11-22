import requests
import json
import urllib3
urllib3.disable_warnings()

auth_file = r"C:\AI-BS\native_studio\xbox_wdp_auth.json"
with open(auth_file, "r") as f:
    cfg = json.load(f)

s = requests.Session()
s.verify = False
s.auth = (cfg["username"], cfg["password"])

endpoints = [
    "/api/networking/networkinterfaces",
    "/api/networking/ipconfig",
    "/api/os/info",
    "/api/resourcemanager/systemperf"
]

for ep in endpoints:
    try:
        r = s.get(f"https://192.168.10.2:11443{ep}", timeout=3)
        print(f"GET {ep} -> HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(json.dumps(data, indent=2)[:500] + "...\n")
    except Exception as e:
        print(f"GET {ep} -> Error: {e}")
