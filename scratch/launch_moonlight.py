import requests
import json
import urllib.parse
import urllib3
urllib3.disable_warnings()

auth_file = r"C:\AI-BS\native_studio\xbox_wdp_auth.json"
with open(auth_file, "r") as f:
    cfg = json.load(f)

s = requests.Session()
s.verify = False
s.auth = (cfg["username"], cfg["password"])

# Get CSRF
s.get("https://192.168.10.2:11443/api/os/info", timeout=3)
csrf = ""
for cookie in s.cookies:
    if cookie.name == "CSRF-Token":
        csrf = cookie.value

headers = {"X-CSRF-Token": csrf} if csrf else {}

# Check apps to find Moonlight's exact RelativeId (AppId)
apps_res = s.get("https://192.168.10.2:11443/api/app/packagemanager/packages", timeout=5)
moonlight_app = None
for a in apps_res.json().get("InstalledPackages", []):
    if "Moonlight" in a.get("Name", "") or "Moonlight" in a.get("PackageFullName", ""):
        moonlight_app = a
        break

print("Moonlight App Info:")
print(json.dumps(moonlight_app, indent=2))

if moonlight_app:
    pfn = moonlight_app.get("PackageFullName")
    # In UWP, AppId is usually PackageFamilyName!App
    p_family = moonlight_app.get("PackageFamilyName", "")
    app_id = moonlight_app.get("AppId", f"{p_family}!App")
    
    # Test launch endpoint
    # POST /api/taskmanager/app?appid=<base64 encoded or raw>
    import base64
    b64_appid = base64.b64encode(app_id.encode()).decode()
    
    url = f"https://192.168.10.2:11443/api/taskmanager/app?appid={urllib.parse.quote(b64_appid)}"
    print(f"Attempting launch: POST {url}")
    r = s.post(url, headers=headers, timeout=5)
    print(f"Launch response: HTTP {r.status_code} - {r.text}")
