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

check_repo("irixaligned/duckstation-uwp")
check_repo("SirMangler/Dolphin-UWP")
check_repo("SirMangler/PPSSPP-UWP")
check_repo("TheWizWikii/Xbox-S-X")
