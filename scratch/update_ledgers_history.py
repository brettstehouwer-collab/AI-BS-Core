import datetime
import os
import shutil

now_dt = datetime.datetime.now()
now_str = now_dt.strftime('%Y-%m-%d')
now_readable = now_dt.strftime('%Y-%m-%d %H:%M:%S')
now_compact = now_dt.strftime('%Y%m%d')

new_version = "5.22.3"
phase = "Phase 19.1"
title = "History Tab Release Log Integration"

# 1. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'r', encoding='utf-8') as f:
    ledger_lines = f.readlines()

new_ledger_lines = []
for line in ledger_lines:
    if line.startswith('**Current Version:**'):
        new_ledger_lines.append(f"**Current Version:** {new_version} ({phase}) ({title})\n")
    elif line.startswith('###|'):
        new_ledger_lines.append(f"###| {now_str} | {new_version} | {title} | Integrated a highly detailed, smooth-scrolling Master Release Log data table into the BullshitEvolutionHistory.jsx component. |\n")
        new_ledger_lines.append(line)
    elif line.startswith('### [') and 'FLUX 3 Image-to-Video Workflow' in line:
        new_ledger_lines.append(f"### [{now_readable}] {title}\n")
        new_ledger_lines.append(f"**AI Rationale:** The user requested the integration of a detailed markdown history table into the AI-BS History Tab.\n")
        new_ledger_lines.append(f"**Technical Specs:**\n")
        new_ledger_lines.append(f"- Appended a new `releaseLogs` state array to `BullshitEvolutionHistory.jsx` containing 9 key historical milestones.\n")
        new_ledger_lines.append(f"- Designed a sleek, dark-mode, glassmorphism `<table>` with `overflow-x-auto` and `scroll-smooth` to accommodate the large text without breaking the 24-column grid.\n")
        new_ledger_lines.append(f"**Modified File List & Fallback Context:**\n")
        new_ledger_lines.append(f"- `C:\\AI-BS\\frontend\\components\\BullshitEvolutionHistory.jsx`\n\n")
        new_ledger_lines.append(line)
    else:
        new_ledger_lines.append(line)

with open(ledger_path, 'w', encoding='utf-8') as f:
    f.writelines(new_ledger_lines)

# 2. Update AI_BS_MASTER_ECOSYSTEM_MANUAL.md
manual_path = r'C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md'
with open(manual_path, 'r', encoding='utf-8') as f:
    manual_lines = f.readlines()

new_manual_lines = []
for i, line in enumerate(manual_lines):
    if line.startswith('## 5.22.2'):
        new_manual_lines.append(f"## {new_version} - {title} ({now_str})\n")
        new_manual_lines.append(f"### {phase}: History Tab Release Log Integration\n")
        new_manual_lines.append(f"**AI Rationale & Implementation:**\n")
        new_manual_lines.append(f"- **Goal:** Provide a detailed, historically accurate Release Log inside the UI.\n")
        new_manual_lines.append(f"- **Implementation:** `BullshitEvolutionHistory.jsx` was augmented with a smooth-scrolling data table containing all major AI-BS milestones from v1.2.0 to v5.22.2.\n\n")
        new_manual_lines.append(line)
    else:
        new_manual_lines.append(line)

with open(manual_path, 'w', encoding='utf-8') as f:
    f.writelines(new_manual_lines)

# 3. Artifact backup and Lineage
artifacts_dir = r'C:\AI-BS\saved_data\artifacts'
notebook_records_dir = r'C:\AI-BS\NotebookLM_Records'

os.makedirs(artifacts_dir, exist_ok=True)
os.makedirs(notebook_records_dir, exist_ok=True)

eco_dest = os.path.join(artifacts_dir, f"{now_compact}_AI_BS_Master_Ecosystem_Manual.md")
shutil.copy(manual_path, eco_dest)

history_file = os.path.join(notebook_records_dir, 'artifact_history.md')
with open(history_file, 'a', encoding='utf-8') as f:
    f.write(f"\n- **{now_readable}**: Persisted Ecosystem Manual to `{eco_dest}` ({phase} - {title}).\n")

print(f"Successfully bumped version to {new_version} and updated ledgers.")
