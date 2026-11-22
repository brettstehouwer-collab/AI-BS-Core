import requests
import urllib3
urllib3.disable_warnings()

try:
    r = requests.get("https://localhost:49001", auth=("admin", "admin"), verify=False, timeout=3)
    print(f"[+] Authenticated Sunshine Web Server Online! Status Code: {r.status_code}")
except Exception as e:
    print(f"[-] Error: {e}")
