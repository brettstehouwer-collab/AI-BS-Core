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
            line = "> **Version:** 8.41.0 (Live Telemetry & Omni-Drive Integration)\n"
        elif line.startswith("### **v8.") and not inserted:
            entry = f"### **v8.41.0 - Live Telemetry & Omni-Drive Integration ({date_str})**\n"
            entry += "- **Feature:** Fully activated the right-hand Split-Pane interfaces.\n"
            entry += "- **Details:** Swapped out the static UI placeholders in `SplitPaneIDEWorkspace.jsx` for the fully functional `BullshitTelemetrySuite` (Aero-Agri telemetry) and `BullshitKnowledgeSuite` (Omni-Drive search), wiring the workspace up for real-world functionality.\n\n"
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
        f.write(f"- [{date_str} {time_str}] Updated AI_BS_MASTER_ECOSYSTEM_MANUAL.md to v8.41.0\n")
        
def append_tasks():
    history_path = r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"- [{date_str} {time_str}] Live Telemetry & Omni-Drive Integration in Split Pane.\n")

update_ledger(
    r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    f"## **[{date_str} {time_str}]** Live Telemetry & Omni-Drive Integration - Version 8.41.0",
    "- **Action:** Replaced static placeholder text in `SplitPaneIDEWorkspace.jsx` with real `BullshitTelemetrySuite` and `BullshitKnowledgeSuite` component imports.\n"
    "- **Rationale:** The user correctly identified that the newly collapsible Split-Pane was rendering non-functional mockups. By mounting the actual components with the correct `activeTab` props, the right pane is now fully functional without wasting space."
)

update_ecosystem_manual()
log_history()
append_tasks()

print("Updates successful.")
