import os
import sys
import time
import urllib.request
import json

TARGET_DIR = r"C:\XboxStaging\Packages"
os.makedirs(TARGET_DIR, exist_ok=True)

PACKAGES = [
    {
        "name": "DuckStation (PS1)",
        "filename": "duckstation-uwp_1.0.0.0_x64_ReleaseUWP.appx",
        "url": "https://github.com/TheWizWikii/Xbox-S-X/releases/download/1.0/duckstation-uwp_1.0.0.0_x64_ReleaseUWP.appx"
    },
    {
        "name": "Dolphin (GameCube/Wii)",
        "filename": "DolphinWinRT_1.1.7.0.appx",
        "url": "https://github.com/TheWizWikii/Xbox-S-X/releases/download/1.0/DolphinWinRT_1.1.7.0.appx"
    },
    {
        "name": "PPSSPP (PSP)",
        "filename": "PPSSPP_UWP_1.17.0.0_x64_UWP_Gold.msix",
        "url": "https://github.com/TheWizWikii/Xbox-S-X/releases/download/1.0/PPSSPP_UWP_1.17.0.0_x64_UWP_Gold.msix"
    },
    {
        "name": "XBSX2 (PS2)",
        "filename": "xbsx2_2.0.2.0_x64.appx",
        "url": "https://github.com/TheWizWikii/Xbox-S-X/releases/download/1.0/xbsx2_2.0.2.0_x64.appx"
    }
]

def download_file(url: str, dest_path: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f"[*] Already exists: {os.path.basename(dest_path)} ({os.path.getsize(dest_path) / (1024*1024):.2f} MB)")
        return True

    print(f"[*] Downloading {os.path.basename(dest_path)}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            block_size = 65536
            start_time = time.time()
            while True:
                buffer = resp.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                pct = (downloaded / total_size * 100) if total_size else 0
                mb = downloaded / (1024 * 1024)
                sys.stdout.write(f"\r    -> {mb:.2f} MB / {total_size/(1024*1024):.2f} MB ({pct:.1f}%)")
                sys.stdout.flush()
            print()
            elapsed = time.time() - start_time
            print(f"[+] Download complete: {os.path.basename(dest_path)} in {elapsed:.2f}s")
            return True
    except Exception as e:
        print(f"\n[-] Download failed for {url}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("DOWNLOADING STANDALONE XBOX UWP EMULATORS")
    print("=" * 70)
    for pkg in PACKAGES:
        dest = os.path.join(TARGET_DIR, pkg["filename"])
        success = download_file(pkg["url"], dest)
        if not success:
            print(f"[!] Warning: Failed to download {pkg['name']}")
    print("\nDownload stage finished.")
