import os, datetime, re
date_str = datetime.date.today().isoformat()
entry = f'''

## [{date_str}] UI/UX & Backend Daemon Fixes
- **AI Rationale:** The backend daemon crashed due to stderr output crashing the PowerShell wrapper. Restarted safely with cmd.exe. Also fixed the SplitPaneIDEWorkspace to prevent UI squashing.
- **Updated Technical Specifications:** Backend operates on port 8080 (recovered). SplitPane layout uses `repeat(auto-fit, minmax(400px, 1fr))` for robust responsiveness.
- **Modified File List:** `C:\\AI-BS\\frontend\\components\\SplitPaneIDEWorkspace.jsx`, Backend runtime arguments.
- **Fallback Context:** If SplitPane breaks, revert to `gridTemplateColumns: showRightPane ? "1fr 1fr" : "1fr"`.
'''
with open(r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md', 'a', encoding='utf-8') as f:
    f.write(entry)

eco_path = r'C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md'
with open(eco_path, 'r', encoding='utf-8') as f:
    eco_content = f.read()

match = re.search(r'v(\d+\.\d+\.)(\d+)', eco_content)
if match:
    old_version = match.group(0)
    new_patch = int(match.group(2)) + 1
    new_version = f'v{match.group(1)}{new_patch}'
    eco_content = eco_content.replace(old_version, new_version)
    with open(eco_path, 'w', encoding='utf-8') as f:
        f.write(eco_content)
else:
    new_version = 'vUNKNOWN'

date_str2 = datetime.date.today().strftime('%Y%m%d')
os.makedirs(r'C:\AI-BS\saved_data\artifacts', exist_ok=True)
with open(fr'C:\AI-BS\saved_data\artifacts\{date_str2}_AI_BS_Master_Ecosystem_Manual.md', 'w', encoding='utf-8') as f:
    f.write(eco_content)

os.makedirs(r'C:\AI-BS\NotebookLM_Records', exist_ok=True)
with open(r'C:\AI-BS\NotebookLM_Records\artifact_history.md', 'a', encoding='utf-8') as f:
    f.write(f'\n- [{datetime.datetime.now().isoformat()}] Saved updated AI_BS_Master_Ecosystem_Manual.md ({new_version})')

print(f'SUCCESS: Ledger updated and ecosystem manual bumped to {new_version}')
