import os
import shutil
import datetime

timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

import sys

task_file = sys.argv[1] if len(sys.argv) > 1 else r"C:\AI-BS\task.md"
task_description = sys.argv[2] if len(sys.argv) > 2 else "Archived Task"

archive_dir = r"C:\AI-BS\Agent_Tasks_History"
chronology_file = r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md"
index_file = r"C:\AI-BS\MASTER_HISTORICAL_INDEX.md"

os.makedirs(archive_dir, exist_ok=True)

if os.path.exists(task_file):
    archive_path = os.path.join(archive_dir, f"task_{timestamp_str}.md")
    shutil.copy2(task_file, archive_path)
    
    # Update Chronology
    if not os.path.exists(chronology_file):
        with open(chronology_file, 'w') as f:
            f.write("# Master Tasks Chronology\n\n")
    
    with open(chronology_file, 'a') as f:
        f.write(f"- **{date_str}**: {task_description}. Archived to `{archive_path}`\n")
        
    print(f"Archived task to {archive_path}")

print("Chronology updated.")
