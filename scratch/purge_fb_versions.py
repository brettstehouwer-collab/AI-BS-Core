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

# Fetch releases first to see what is currently deployed/active on live channel
rel_url = 'https://firebasehosting.googleapis.com/v1beta1/projects/ai-bs-dashboard/sites/ai-bs-dashboard/channels/live/releases'
req = urllib.request.Request(rel_url, headers=headers)
live_version_name = None
try:
    with urllib.request.urlopen(req) as resp:
        rel_data = json.loads(resp.read().decode('utf-8'))
        releases = rel_data.get('releases', [])
        if releases:
            live_version_name = releases[0].get('version', {}).get('name')
            print(f"Active Live Release Version: {live_version_name}")
except urllib.error.HTTPError as e:
    print(f"Failed to fetch releases: {e.code}")

# Now fetch all versions
url = 'https://firebasehosting.googleapis.com/v1beta1/projects/ai-bs-dashboard/sites/ai-bs-dashboard/versions'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    versions = res.get('versions', [])

deleted_count = 0
deleted_mb = 0

for v in versions:
    v_name = v.get('name')
    status = v.get('status')
    size_mb = round(int(v.get('versionBytes', 0)) / (1024 * 1024), 2)

    # Never delete the active live version
    if v_name == live_version_name:
        print(f"SKIPPING active live version: {v_name}")
        continue

    # Delete expired or old versions
    del_url = f"https://firebasehosting.googleapis.com/v1beta1/{v_name}"
    del_req = urllib.request.Request(del_url, headers=headers, method='DELETE')
    try:
        with urllib.request.urlopen(del_req) as del_resp:
            print(f"DELETED: {v_name} ({size_mb} MB) -> {del_resp.status}")
            deleted_count += 1
            deleted_mb += size_mb
    except urllib.error.HTTPError as e:
        print(f"Error deleting {v_name}: {e.code} - {e.read().decode('utf-8')}")

print(f"\nDone! Purged {deleted_count} versions, freed approximately {round(deleted_mb / 1024, 2)} GB of Firebase Hosting storage.")
