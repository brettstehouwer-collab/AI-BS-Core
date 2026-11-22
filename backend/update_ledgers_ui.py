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
            line = "> **Version:** 8.40.0 (Split-Pane Chat UI Toggle Update)\n"
        elif line.startswith("### **v8.") and not inserted:
            entry = f"### **v8.40.0 - Split-Pane Chat UI Toggle Update ({date_str})**\n"
            entry += "- **Feature:** Updated the `SplitPaneIDEWorkspace` to collapse the right telemetry pane by default, offering a significantly wider AI-BS chat area.\n"
            entry += "- **Details:** Added a `showRightPane` state and a toggle button to conditionally render the `1fr 1fr` grid layout vs a full-width `1fr` layout, resolving chat overflow constraints.\n\n"
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
        f.write(f"- [{date_str} {time_str}] Updated AI_BS_MASTER_ECOSYSTEM_MANUAL.md to v8.40.0\n")
        
def append_tasks():
    history_path = r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"- [{date_str} {time_str}] Split-Pane Chat UI Toggle Update.\n")

update_ledger(
    r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
    f"## **[{date_str} {time_str}]** Split-Pane Chat UI Toggle Update - Version 8.40.0",
    "- **Action:** Updated `SplitPaneIDEWorkspace.jsx` to hide the right telemetry pane by default, and introduced a toggle button in the chat header to swap between 1-pane and 2-pane layouts.\n"
    "- **Rationale:** The fixed `1fr 1fr` grid caused the chat box to be too cramped on smaller displays. Hiding the telemetry pane by default provides an expanded, distraction-free chat experience while maintaining rapid access to system observations when needed."
)

update_ecosystem_manual()
log_history()
append_tasks()

print("Updates successful.")
