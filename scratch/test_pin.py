import requests
import json
import urllib3
urllib3.disable_warnings()

auth_file = r"C:\AI-BS\native_studio\xbox_wdp_auth.json"
with open(auth_file, "r") as f:
    cfg = json.load(f)

session = requests.Session()
session.verify = False
session.auth = (cfg["username"], cfg["password"])

endpoints = [
    "/api/common/pin",
    "/api/devkit/pin",
    "/api/os/pin",
    "/api/app/packagemanager/pin",
    "/api/devicemanager/pin",
    "/ext/pin"
]

for ep in endpoints:
    try:
        r = session.get(f"https://192.168.10.2:11443{ep}", timeout=2)
        print(f"GET {ep} -> {r.status_code}")
    except Exception as e:
        print(f"GET {ep} -> Error: {e}")

