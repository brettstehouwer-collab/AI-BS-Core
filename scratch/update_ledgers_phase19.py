import datetime
import os
import shutil

now_dt = datetime.datetime.now()
now_str = now_dt.strftime('%Y-%m-%d')
now_readable = now_dt.strftime('%Y-%m-%d %H:%M:%S')
now_compact = now_dt.strftime('%Y%m%d')

new_version = "5.22.2"
phase = "Phase 19"
title = "FLUX 3 Image-to-Video Workflow UI Integration"

# 1. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'r', encoding='utf-8') as f:
    ledger_lines = f.readlines()

new_ledger_lines = []
for line in ledger_lines:
    if line.startswith('**Current Version:**'):
        new_ledger_lines.append(f"**Current Version:** {new_version} ({phase}) ({title})\n")
    elif line.startswith('###|'):
        # Insert the new table row
        new_ledger_lines.append(f"###| {now_str} | {new_version} | {title} | Integrated FLUX 3 Image-to-Video ComfyUI JSON format pipeline with dynamic API retrieval, and added React interface component to trigger custom workflows on demand. |\n")
        new_ledger_lines.append(line)
    elif line.startswith('### [') and 'Creation Suite Flexbox' in line:
        # Insert the new section
        new_ledger_lines.append(f"### [{now_readable}] {title}\n")
        new_ledger_lines.append(f"**AI Rationale:** The user required the ability to trigger the new FLUX 3 Image-to-Video JSON workflow, as well as any other workflow 'on deck', directly from the frontend UI without manually editing code each time.\n")
        new_ledger_lines.append(f"**Technical Specs:**\n")
        new_ledger_lines.append(f"- Converted ComfyUI FLUX 3 UI-format JSON to API-format JSON and saved as `flux3_i2v_api.json`.\n")
        new_ledger_lines.append(f"- Modified `comfyui_client.py`'s `inject_prompt_into_workflow` function to dynamically inject `prompt_text` and randomized seeds into `Flux3ImageToVideoNode` nodes.\n")
        new_ledger_lines.append(f"- Updated `ComfyUIWorkflowTrigger.tsx` to dynamically fetch all available backend workflows via `http://127.0.0.1:8000/api/comfyui/workflows` and render a trigger button for each.\n")
        new_ledger_lines.append(f"**Modified File List & Fallback Context:**\n")
        new_ledger_lines.append(f"- `C:\\AI-BS\\backend\\comfyui_workflows\\flux3_i2v_api.json` (NEW)\n")
        new_ledger_lines.append(f"- `C:\\AI-BS\\backend\\comfyui_client.py`\n")
        new_ledger_lines.append(f"- `C:\\AI-BS\\frontend\\src\\components\\ComfyUIWorkflowTrigger.tsx`\n\n")
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
    if line.startswith('## 5.22.1'):
        # Insert new manual section right before the old one
        new_manual_lines.append(f"## {new_version} - {title} ({now_str})\n")
        new_manual_lines.append(f"### {phase}: Dynamic UI Workflow Triggering\n")
        new_manual_lines.append(f"**AI Rationale & Implementation:**\n")
        new_manual_lines.append(f"- **Goal:** Support dynamic workflow discovery and FLUX 3 Image-to-Video generation directly from the React frontend.\n")
        new_manual_lines.append(f"- **Implementation:** `ComfyUIWorkflowTrigger.tsx` was refactored to fetch workflows dynamically from `/api/comfyui/workflows` instead of hardcoding SDXL/Wan2.1 logic. A translated API-format JSON (`flux3_i2v_api.json`) was added for the new pipeline, and `comfyui_client.py` was extended to parse `Flux3ImageToVideoNode` inputs.\n\n")
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
