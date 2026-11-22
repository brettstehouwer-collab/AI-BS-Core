import urllib.request
import json

def check_repo(repo):
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req).read().decode())
        print(f"\nRepo: {repo} (Tag: {data.get('tag_name')})")
        for a in data.get("assets", []):
            print(f"  {a['name']} ({a['size']} bytes) -> {a['browser_download_url']}")
    except Exception as e:
        print(f"Error checking {repo}: {e}")

check_repo("TheElixZammuto/moonlight-xbox")
check_repo("hrydgard/ppsspp")
check_repo("flyinghead/flycast")
check_repo("diasurgical/devilutionX")
