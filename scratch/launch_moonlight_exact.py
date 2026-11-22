import requests
import json
import base64
import urllib.parse
import urllib3
urllib3.disable_warnings()

auth_file = r"C:\AI-BS\native_studio\xbox_wdp_auth.json"
with open(auth_file, "r") as f:
    cfg = json.load(f)

s = requests.Session()
s.verify = False
s.auth = (cfg["username"], cfg["password"])

s.get("https://192.168.10.2:11443/api/os/info", timeout=3)
csrf = ""
for cookie in s.cookies:
    if cookie.name == "CSRF-Token":
        csrf = cookie.value

headers = {"X-CSRF-Token": csrf} if csrf else {}

app_id = "50497EliaZammuto.MoonlightUWP_wjq6j17wd9wbe!App"
b64_appid = base64.b64encode(app_id.encode()).decode()

url = f"https://192.168.10.2:11443/api/taskmanager/app?appid={urllib.parse.quote(b64_appid)}"
print(f"Launching exact RelativeId: {app_id}")
r = s.post(url, headers=headers, timeout=5)
print(f"Launch response: HTTP {r.status_code} - {r.text}")
