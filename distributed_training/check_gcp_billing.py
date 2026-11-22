import urllib.request
import urllib.error
import json
import google.auth
from google.auth.transport.requests import Request

creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(Request())

projects = [
    'ai-bs-dashboard',
    'ai-bs-500513',
    'secure-charger-401dl',
    'com-example-sandoxbuild-9ad48',
    'hidef-medium-5lll2',
    'gen-lang-client-0901521318'
]

print("=" * 60)
print("GOOGLE CLOUD BILLING STATUS CHECK ACROSS PROJECTS")
print("=" * 60)

for p in projects:
    url = f"https://cloudbilling.googleapis.com/v1/projects/{p}/billingInfo"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            info = json.loads(resp.read().decode())
            print(f"Project: {p:<30} | BillingEnabled: {info.get('billingEnabled', False)} | Account: {info.get('billingAccountName', 'None')}")
    except urllib.error.HTTPError as e:
        print(f"Project: {p:<30} | Error HTTP {e.code}")

print("=" * 60)

