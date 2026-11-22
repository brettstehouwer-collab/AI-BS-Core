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
    r'C:\AI-BS\scripts\package_update_payload.ps1',
    r'C:\AI-BS\frontend\components\OperationsAuditHubTab.jsx',
    r'C:\AI-BS\frontend\src\components\OperationsAuditHubTab.jsx'
]

replacements = [
    ('5.200.0', '5.201.0'),
    ('v5.200.0', 'v5.201.0')
]

updated_count = 0
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
            updated_count += 1

print(f"Version sweep to v5.201.0 complete. Updated {updated_count} files.")
