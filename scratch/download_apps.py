import os
import urllib.request
import time

DEST_DIR = r"C:\XboxStaging\Packages"
os.makedirs(DEST_DIR, exist_ok=True)

DOWNLOADS = [
    ("Microsoft.UI.Xaml.2.7.appx", "https://github.com/TheElixZammuto/moonlight-xbox/releases/download/1.18.2/Microsoft.UI.Xaml.2.7.appx"),
    ("moonlight-xbox-dx.msixbundle", "https://github.com/TheElixZammuto/moonlight-xbox/releases/download/1.18.2/moonlight-xbox-dx_1.18.2.0_x64.msixbundle"),
    ("flycast.appx", "https://github.com/flyinghead/flycast/releases/download/v2.7/flycast-2.7.appx"),
    ("kodi-21.2.msix", "https://mirrors.kodi.tv/releases/windows/UWP/kodi-21.2-Omega_21.2.0.0-x64.msix")
]

for filename, url in DOWNLOADS:
    target = os.path.join(DEST_DIR, filename)
    if os.path.exists(target) and os.path.getsize(target) > 1000:
        print(f"[SKIP] {filename} already exists ({os.path.getsize(target)/(1024*1024):.2f} MB)")
        continue
    print(f"[*] Downloading: {filename} from {url}...")
    start = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(target, "wb") as out:
        chunk = resp.read(1024 * 1024)
        while chunk:
            out.write(chunk)
            chunk = resp.read(1024 * 1024)
    elapsed = max(time.time() - start, 0.01)
    size_mb = os.path.getsize(target) / (1024 * 1024)
    print(f" [+] Saved: {filename} ({size_mb:.2f} MB in {elapsed:.1f}s, {size_mb/elapsed:.2f} MB/s)")

print("\n[+] All packages staged successfully in", DEST_DIR)
