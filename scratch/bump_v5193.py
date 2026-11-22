import os

files_to_update = [
    r'C:\AI-BS\frontend\package.json',
    r'C:\AI-BS\frontend\public\updates\version.json',
    r'C:\AI-BS\backend\routers\updater_router.py',
    r'C:\AI-BS\frontend\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\src\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\src\components\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\components\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\src\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\components\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\src\components\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\components\ChatTab.jsx',
    r'C:\AI-BS\frontend\src\components\ChatTab.jsx',
    r'C:\AI-BS\frontend\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\src\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\components\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\src\components\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\frontend\src\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\frontend\components\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\frontend\src\components\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\frontend\App.jsx',
    r'C:\AI-BS\frontend\components\Sidebar.jsx',
    r'C:\AI-BS\frontend\src\components\Sidebar.jsx',
    r'C:\AI-BS\installer\AI_BS_Studio_Setup.iss',
    r'C:\AI-BS\scripts\package_update_payload.ps1'
]

replacements = [
    ('5.192.0', '5.193.0'),
    ('v5.192.0', 'v5.193.0')
]

for p in files_to_update:
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        orig = content
        for old, new in replacements:
            content = content.replace(old, new)
        if content != orig:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Updated: {p}')

# Also update release notes in version.json and package_update_payload.ps1
version_json_path = r'C:\AI-BS\frontend\public\updates\version.json'
if os.path.exists(version_json_path):
    with open(version_json_path, 'r', encoding='utf-8') as f:
        vj = f.read()
    vj = vj.replace(
        "Business Email Client Compliance API, Dynamic Counts, Sender Spacing & Campaign Math.",
        "Stehouwer Wave Studio Live Recording Microphone Permissions & Resilient Audio Ingestion Engine."
    )
    with open(version_json_path, 'w', encoding='utf-8') as f:
        f.write(vj)
    print("Updated release notes in version.json")

print("Version sweep to v5.193.0 complete.")
