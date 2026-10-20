import os
import re
import json

old_version_num = "5.316.0"
new_version_num = "5.317.0"
new_version_tag = f"v{new_version_num}"
new_release_name = f"{new_version_tag}-autonomous-expansion-sentinel-federation-storyboard"

# 1. Update version.txt
with open(r"C:\AI-BS\version.txt", "w", encoding="utf-8") as f:
    f.write(f"{new_version_tag}\n")
print(f"Updated C:\\AI-BS\\version.txt -> {new_version_tag}")

# 2. Update frontend/package.json
pkg_path = r"C:\AI-BS\frontend\package.json"
with open(pkg_path, "r", encoding="utf-8") as f:
    pkg = json.load(f)
pkg["version"] = new_version_num
with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg, f, indent=2)
print(f"Updated frontend/package.json -> {new_version_num}")

# 3. Update version.json
vjson_path = r"C:\AI-BS\frontend\public\version.json"
with open(vjson_path, "w", encoding="utf-8") as f:
    json.dump({
        "version": new_version_num,
        "release_tag": new_release_name,
        "release_date": "2026-10-14",
        "description": "Autonomous Self-Healing Sentinel, Vast.ai Node Federation, Screenplay-to-Movie Headless Blender VSE, Commercial B2B Harvester & CRO Support Backtesting Sandbox."
    }, f, indent=2)
print("Updated frontend/public/version.json")

# 4. Update sw.js
sw_path = r"C:\AI-BS\frontend\public\sw.js"
if os.path.exists(sw_path):
    with open(sw_path, "r", encoding="utf-8") as f:
        sw_content = f.read()
    sw_content = sw_content.replace(old_version_num, new_version_num)
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)
    print("Updated frontend/public/sw.js")

# 5. Sweep all frontend components in all 4 mirrors
frontend_root = r"C:\AI-BS\frontend"
badge_files = [
    r"src\components\ChatTab.jsx",
    r"src\components\ChatToolControlBar.jsx",
    r"src\components\MobileGeminiChat.jsx",
    r"src\components\MobileStehouwerChat.jsx",
    r"src\components\NdaModuleTab.jsx",
    r"src\components\PersonalBrandStudioTab.jsx",
    r"src\components\Sidebar.jsx",
    r"src\components\TopNavbar.jsx",
    r"src\components\MediaStudioTab.jsx",
    r"src\components\PhoneRepairGuideTab.jsx",
    r"src\components\ClusterEngineTab.jsx",
    r"components\ChatTab.jsx",
    r"components\ChatToolControlBar.jsx",
    r"components\MobileGeminiChat.jsx",
    r"components\MobileStehouwerChat.jsx",
    r"components\NdaModuleTab.jsx",
    r"components\PersonalBrandStudioTab.jsx",
    r"components\Sidebar.jsx",
    r"components\TopNavbar.jsx",
    r"components\MediaStudioTab.jsx",
    r"components\PhoneRepairGuideTab.jsx",
    r"components\ClusterEngineTab.jsx",
    r"src\components\components\ChatTab.jsx",
    r"src\components\components\ChatToolControlBar.jsx",
    r"src\components\components\MobileGeminiChat.jsx",
    r"src\components\components\MobileStehouwerChat.jsx",
    r"src\components\components\NdaModuleTab.jsx",
    r"src\components\components\PersonalBrandStudioTab.jsx",
    r"src\components\components\Sidebar.jsx",
    r"src\components\components\TopNavbar.jsx",
    r"src\components\components\MediaStudioTab.jsx",
    r"src\components\components\PhoneRepairGuideTab.jsx",
    r"src\components\components\ClusterEngineTab.jsx",
    r"components\components\ChatTab.jsx",
    r"components\components\ChatToolControlBar.jsx",
    r"components\components\MobileGeminiChat.jsx",
    r"components\components\MobileStehouwerChat.jsx",
    r"components\components\NdaModuleTab.jsx",
    r"components\components\PersonalBrandStudioTab.jsx",
    r"components\components\Sidebar.jsx",
    r"components\components\TopNavbar.jsx",
    r"components\components\MediaStudioTab.jsx",
    r"components\components\PhoneRepairGuideTab.jsx",
    r"components\components\ClusterEngineTab.jsx",
]

for rel in badge_files:
    full = os.path.join(frontend_root, rel)
    if os.path.exists(full):
        with open(full, "r", encoding="utf-8") as f:
            c = f.read()
        if old_version_num in c or f"v{old_version_num}" in c:
            c = c.replace(f"v{old_version_num}", f"v{new_version_num}")
            c = c.replace(old_version_num, new_version_num)
            with open(full, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"Swept badge in {rel}")

print("Version sweep complete -> v5.317.0")
