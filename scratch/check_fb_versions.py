import json
import urllib.request
import urllib.error

cfg_path = r"C:\Users\footb\.config\configstore\firebase-tools.json"
with open(cfg_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

token = data['tokens']['access_token']
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

url = 'https://firebasehosting.googleapis.com/v1beta1/projects/ai-bs-dashboard/sites/ai-bs-dashboard/versions'
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        versions = res.get('versions', [])
        print(f"Total versions returned: {len(versions)}")
        for v in versions:
            name = v.get('name')
            status = v.get('status')
            created = v.get('createTime')
            files = v.get('fileCount')
            size_mb = round(int(v.get('versionBytes', 0)) / (1024 * 1024), 2)
            print(f"Version: {name} | Status: {status} | Created: {created} | Files: {files} | SizeMB: {size_mb}")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} - {e.read().decode('utf-8')}")
