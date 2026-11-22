import os
import re
from datetime import datetime
import shutil

date_str = datetime.now().strftime("%Y-%m-%d")
time_str = datetime.now().strftime("%H:%M:%S")

def update_ledger(path, entry_header, entry_body):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    inserted = False
    for line in lines:
        if re.match(r'^## \*\*\[[0-9-]{10} [0-9:]{8}\]\*\*', line) and not inserted:
            new_lines.append(f"{entry_header}\n\n{entry_body}\n\n")
            inserted = True
        new_lines.append(line)
        
    if not inserted:
        new_lines.append(f"\n{entry_header}\n\n{entry_body}\n\n")
        
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def update_ecosystem_manual():
    path = r"C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    inserted = False
    for line in lines:
        if line.startswith("> **Version:**"):
            line = "> **Version:** 8.39.0 (HTTP 500 LLM Safety Hotfix)\n"
        elif line.startswith("### **v8.") and not inserted:
            entry = f"### **v8.39.0 - HTTP 500 LLM Safety Hotfix ({date_str})**\n"
            entry += "- **Feature:** Patched an edge case where missing `httpx` imports inside `AI_BS_Backend.py` caused HTTP 500 UnboundLocalErrors, triggering false Llama Guard panics on inputs like \"sex\".\n"
            entry += "- **Details:** Moved `import httpx` to global scope in `chat_endpoint`. Validated that the Stehouwer LLM safety filters (S1/S3/S4) are functioning exactly as intended via correct backend model falling back.\n\n"
            new_lines.append(entry)
            inserted = True
        new_lines.append(line)
        
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    # Copy to artifacts
    artifacts_dir = r"C:\AI-BS\saved_data\artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)
    shutil.copy(path, os.path.join(artifacts_dir, f"{date_str.replace('-', '')}_AI_BS_Master_Ecosystem_Manual.md"))

def log_history():
    history_path = r"C:\AI-BS\NotebookLM_Records\artifact_history.md"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"- [{date_str} {time_str}] Updated AI_BS_MASTER_ECOSYSTEM_MANUAL.md to v8.39.0\n")
        
def append_tasks():
    history_path = r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"- [{date_str} {time_str}] Fixed HTTP 500 Bug in Stehouwer LLM safety module.\n")

update_ledger(
    r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    f"## **[{date_str} {time_str}]** HTTP 500 UnboundLocalError Hotfix (Safety Integration) - Version 8.39.0",
    "- **Action:** Patched `chat_endpoint` in `AI_BS_Backend.py` to fix an HTTP 500 `UnboundLocalError` triggered by missing `httpx` imports when efficiency mode was disabled.\n"
    "- **Rationale:** The Stehouwer LLM safety filter integration caused a fatal edge case crash (HTTP 500) because the script assumed `httpx` was loaded globally, but it was only imported under the efficiency mode flag. By fixing this, the API gracefully falls back and resolves models like `stehouwer_qwen`, fully honoring Llama Guard S1/S3/S4 requirements."
)

update_ecosystem_manual()
log_history()
append_tasks()

print("Updates successful.")
