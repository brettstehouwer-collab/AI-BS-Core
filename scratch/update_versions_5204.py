import os

files = [
    r'C:\AI-BS\frontend\package.json',
    r'C:\AI-BS\frontend\public\version.json',
    r'C:\AI-BS\frontend\public\updates\version.json',
    r'C:\AI-BS\frontend\dist\version.json',
    r'C:\AI-BS\frontend\dist\updates\version.json',
    r'C:\Program Files\AI-BS Sovereign Studio\frontend_dist\version.json',
    r'C:\Program Files\AI-BS Sovereign Studio\frontend_dist\updates\version.json',
    r'C:\AI-BS\backend\routers\updater_router.py',
    r'C:\AI-BS\frontend\App.jsx',
    r'C:\AI-BS\frontend\src\components\ChatTab.jsx',
    r'C:\AI-BS\frontend\components\ChatTab.jsx',
    r'C:\AI-BS\frontend\src\components\Sidebar.jsx',
    r'C:\AI-BS\frontend\components\Sidebar.jsx',
    r'C:\AI-BS\frontend\src\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\src\components\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\components\components\TopNavbar.jsx',
    r'C:\AI-BS\frontend\src\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\src\components\components\SystemUpdateModal.jsx',
    r'C:\AI-BS\frontend\src\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\src\components\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\components\components\PhoneRepairGuideTab.jsx',
    r'C:\AI-BS\frontend\src\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\frontend\components\PersonalBrandStudioTab.jsx',
    r'C:\AI-BS\installer\AI_BS_Studio_Setup.iss',
    r'C:\AI-BS\scripts\package_update_payload.ps1',
    r'C:\AI-BS\ingest_manifest.json'
]

updated_count = 0
for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
        if '5.203.0' in content:
            new_content = content.replace('5.203.0', '5.204.0')
            with open(f, 'w', encoding='utf-8') as fp:
                fp.write(new_content)
            print(f"Updated: {f}")
            updated_count += 1
        else:
            print(f"No match: {f}")
    else:
        print(f"Missing: {f}")

print(f"Total updated to 5.204.0: {updated_count}")
