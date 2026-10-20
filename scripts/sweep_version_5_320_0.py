import os
import re
import json
import subprocess
import sys

new_version_num = "5.320.0"
new_version_tag = f"v{new_version_num}"
new_release_tag = f"{new_version_tag}-broadcast-studio-preview-ping-rtmp"

print(f"Sweeping ecosystem version to {new_version_tag}...")

# 1. Update version.txt
with open(r"C:\AI-BS\version.txt", "w", encoding="utf-8") as f:
    f.write(f"{new_version_tag}\n")
print(f"[OK] Updated version.txt -> {new_version_tag}")

# 2. Update frontend/package.json
pkg_path = r"C:\AI-BS\frontend\package.json"
if os.path.exists(pkg_path):
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
    pkg["version"] = new_version_num
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(pkg, f, indent=2)
    print(f"[OK] Updated frontend/package.json -> {new_version_num}")

# 3. Update root package.json
root_pkg_path = r"C:\AI-BS\package.json"
if os.path.exists(root_pkg_path):
    with open(root_pkg_path, "r", encoding="utf-8") as f:
        root_pkg = json.load(f)
    root_pkg["version"] = new_version_num
    with open(root_pkg_path, "w", encoding="utf-8") as f:
        json.dump(root_pkg, f, indent=2)
    print(f"[OK] Updated root package.json -> {new_version_num}")

# 4. Update frontend/public/version.json
vjson_path = r"C:\AI-BS\frontend\public\version.json"
if os.path.exists(vjson_path):
    with open(vjson_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": new_version_num,
            "release_tag": new_release_tag,
            "release_date": "2026-10-15",
            "description": "Stehouwer Publishing Broadcast Studio Architecture: Studio A/B Preview Engine, Safe-Area Composition Overlays, Multi-Threaded Real-Time Ingest Ping Diagnostics, Streaming Platform Compliance & Standards Enforcement (Twitch, YouTube 4K, Kick, TikTok, Sovereign SRT)."
        }, f, indent=2)
    print("[OK] Updated frontend/public/version.json")

# 5. Update installer_wizard.py
installer_wizard = r"C:\AI-BS\native_studio\installer_wizard.py"
if os.path.exists(installer_wizard):
    with open(installer_wizard, "r", encoding="utf-8") as f:
        iw_content = f.read()
    iw_content = iw_content.replace('"5.317.0"', f'"{new_version_num}"')
    with open(installer_wizard, "w", encoding="utf-8") as f:
        f.write(iw_content)
    print("[OK] Updated native_studio/installer_wizard.py")

# 6. Sweep badges in canonical frontend/src/components
canonical_dir = r"C:\AI-BS\frontend\src\components"
swept_files = []
for root, _, files in os.walk(canonical_dir):
    for file in files:
        if file.endswith((".jsx", ".js")):
            fp = os.path.join(root, file)
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # replace older versions v5.317.0, v5.318.0, v5.319.0
            new_content = re.sub(r'v5\.31[0-9]\.0', f'v{new_version_num}', content)
            if new_content != content:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(new_content)
                swept_files.append(file)

print(f"[OK] Swept badges in canonical components: {len(swept_files)} files updated ({', '.join(swept_files[:5])}...)")

# 7. Synchronize all 4 mirrors
sync_script = r"C:\AI-BS\scripts\sync_mirrors.py"
res = subprocess.run([sys.executable, sync_script], capture_output=True, text=True)
print(f"[OK] sync_mirrors.py returned {res.returncode}")

print("Version sweep complete -> v5.320.0")
