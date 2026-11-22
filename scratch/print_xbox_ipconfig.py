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

r = s.get("https://192.168.10.2:11443/api/networking/ipconfig", timeout=3)
data = r.json()
print("=== XBOX ONE IP CONFIGURATION ===")
for adapter in data.get("Adapters", []):
    if adapter.get("Type") == "Ethernet" and "192.168.10.2" in str(adapter):
        print(json.dumps(adapter, indent=2))


