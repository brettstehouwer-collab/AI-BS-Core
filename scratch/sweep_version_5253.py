import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

target_files = [
    r"C:\AI-BS\frontend\App.jsx",
    r"C:\AI-BS\frontend\package.json",
    r"C:\AI-BS\frontend\public\sw.js",
    r"C:\AI-BS\frontend\public\version.json",
    r"C:\AI-BS\frontend\public\updates\version.json",
    r"C:\AI-BS\frontend\src\components\ChatTab.jsx",
    r"C:\AI-BS\frontend\src\components\Sidebar.jsx",
    r"C:\AI-BS\frontend\src\components\TopNavbar.jsx",
    r"C:\AI-BS\frontend\src\components\components\ChatTab.jsx",
    r"C:\AI-BS\frontend\src\components\components\Sidebar.jsx",
    r"C:\AI-BS\frontend\src\components\components\TopNavbar.jsx",
    r"C:\AI-BS\frontend\components\ChatTab.jsx",
    r"C:\AI-BS\frontend\components\Sidebar.jsx",
    r"C:\AI-BS\frontend\components\TopNavbar.jsx",
    r"C:\AI-BS\frontend\components\components\Sidebar.jsx",
    r"C:\AI-BS\frontend\components\components\TopNavbar.jsx",
    r"C:\AI-BS\trainer_frontend\package.json",
    r"C:\AI-BS\trainer_frontend\src\renderer\src\App.tsx",
]

for tf in target_files:
    if os.path.exists(tf):
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if "5.252.0" in content:
            new_content = content.replace("5.252.0", "5.253.0")
            with open(tf, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {os.path.relpath(tf, r'C:\AI-BS')} to v5.253.0")
        else:
            print(f"Skipped {os.path.relpath(tf, r'C:\AI-BS')} (no 5.252.0 found)")
