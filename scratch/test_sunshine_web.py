import requests
import urllib3
urllib3.disable_warnings()

try:
    r = requests.get("https://localhost:49001", verify=False, timeout=3)
    print(f"[+] Sunshine Web Server Online! Status Code: {r.status_code}")
    print(f"[+] Title or text snippet: {r.text[:200]}")
except Exception as e:
    print(f"[-] Error: {e}")
