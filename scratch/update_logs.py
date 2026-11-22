import os
import shutil
from datetime import datetime
import re

now = datetime.now()
timestamp_str = now.strftime("%Y%m%d_%H%M%S")
date_str = now.strftime("%Y-%m-%d %H:%M:%S")

app_data_dir = r"C:\Users\footb\.gemini\antigravity-ide\brain\eb5b1a40-4bc0-4e2e-834c-c5cb7e3e54eb"
task_file = os.path.join(app_data_dir, "task.md")
plan_file = os.path.join(app_data_dir, "implementation_plan.md")

aibs_dir = r"C:\AI-BS"
tasks_hist = os.path.join(aibs_dir, "Agent_Tasks_History")
plans_hist = os.path.join(aibs_dir, "Agent_Implementation_Plans_History")
saved_artifacts = os.path.join(aibs_dir, "saved_data", "artifacts")
notebook_records = os.path.join(aibs_dir, "NotebookLM_Records")

# Ensure dirs exist
for d in [tasks_hist, plans_hist, saved_artifacts, notebook_records]:
    os.makedirs(d, exist_ok=True)

# Copy files
task_dest = os.path.join(tasks_hist, f"task_{timestamp_str}.md")
plan_dest = os.path.join(plans_hist, f"implementation_plan_{timestamp_str}.md")
if os.path.exists(task_file):
    shutil.copy(task_file, task_dest)
if os.path.exists(plan_file):
    shutil.copy(plan_file, plan_dest)

# Append to chronologies
def append_to_file(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{content}\n")

append_to_file(os.path.join(aibs_dir, "MASTER_TASKS_CHRONOLOGY.md"), f"- [{date_str}] Banquet Architect Phase 2 - Tasks completed (saved to {task_dest})")
append_to_file(os.path.join(aibs_dir, "MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md"), f"- [{date_str}] Banquet Architect Phase 2 - Plan implemented (saved to {plan_dest})")
append_to_file(os.path.join(aibs_dir, "MASTER_HISTORICAL_INDEX.md"), f"- [{date_str}] Banquet Architect Phase 2 Updates Added.")

# Append to Architectural Ledger
ledger_entry = f"""
## [{date_str}] Banquet Architect Phase 2 (AI Assistant & Voice)
- **AI Rationale:** Enhanced `BanquetArchitectTab.jsx` with Web Speech API for voice transcription without needing a backend model, optimizing speed. Updated `demo_noto.py` NLP parser to inject `spawnActors` and `materialOverride`. Added explicit offline handling for Unreal Engine Web Remote Control.
- **Technical Specs:** Backend API runs `handle_media_assistant_nlp` querying `qwen2.5-coder:latest` on port 11434. Unreal Remote Control target is `127.0.0.1:30010`.
- **User Manual:** Brett/Sean/Julie can now click the microphone icon in the AI Assistant panel to speak natural language scene setup commands. If Unreal Engine is offline, the app displays a clear warning instead of silently failing.
- **Modified Files:** `C:\\AI-BS\\frontend\\components\\BanquetArchitectTab.jsx`, `C:\\AI-BS\\backend\\demo_noto.py`.
"""
append_to_file(os.path.join(aibs_dir, "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"), ledger_entry)

# Bump Ecosystem Manual version
manual_path = os.path.join(aibs_dir, "docs", "AI_BS_MASTER_ECOSYSTEM_MANUAL.md")
if os.path.exists(manual_path):
    with open(manual_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Try to find version line like "Version: 5.0.0" or "v5.0.0"
    def replacer(match):
        ver = match.group(1)
        parts = ver.split('.')
        parts[1] = str(int(parts[1]) + 1) # Bump minor version
        new_ver = '.'.join(parts)
        return f"{match.group(0).replace(ver, new_ver)}"
    
    new_content, count = re.subn(r"(?i)(?:version[: ]*|v)(\d+\.\d+\.\d+)", replacer, content)
    if count == 0:
        new_content = f"Version: 1.1.0\n\n" + content # default if not found
        
    with open(manual_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    # Persist copy
    copy_path = os.path.join(saved_artifacts, f"{now.strftime('%Y%m%d')}_AI_BS_Master_Ecosystem_Manual.md")
    shutil.copy(manual_path, copy_path)
    
    # Log lineage
    history_path = os.path.join(notebook_records, "artifact_history.md")
    append_to_file(history_path, f"- [{date_str}] Updated Ecosystem Manual for Banquet Architect Phase 2. Saved as {copy_path}.")

print("Logs and history updated successfully.")
