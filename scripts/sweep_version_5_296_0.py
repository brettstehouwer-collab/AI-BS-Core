import os
import re
import json

new_version_num = "5.296.0"
new_version_tag = f"v{new_version_num}"
new_release_name = f"{new_version_tag}-stehouwer-17-model-swarm-and-brain-vault"

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
        "release_date": "2026-09-16",
        "description": "Stehouwer LLM 17-Model Unrestricted Fleet, 175-Session Brain Ingestion (139K Records / 67K Vectors), and Port 8080 Lifespan Stabilization."
    }, f, indent=2)
print(f"Updated frontend/public/version.json")

# 4. Update sw.js
sw_path = r"C:\AI-BS\frontend\public\sw.js"
if os.path.exists(sw_path):
    with open(sw_path, "r", encoding="utf-8") as f:
        sw_content = f.read()
    sw_content = re.sub(r'v5\.295\.0', new_version_num, sw_content)
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
]

for rel_path in badge_files:
    full_p = os.path.join(frontend_root, rel_path)
    if os.path.exists(full_p):
        with open(full_p, "r", encoding="utf-8") as f:
            content = f.read()
        updated = content.replace("5.295.0", new_version_num)
        with open(full_p, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Swept badge in: {rel_path}")

print("All badges swept successfully!")
