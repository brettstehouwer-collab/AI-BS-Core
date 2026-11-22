import os
import shutil
import datetime

now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
task_src = r'C:\Users\footb\.gemini\antigravity-ide\brain\8b2f648b-cacb-4cf7-b0d8-22d98ba4ff00\task.md'
plan_src = r'C:\Users\footb\.gemini\antigravity-ide\brain\8b2f648b-cacb-4cf7-b0d8-22d98ba4ff00\implementation_plan.md'

task_dest_name = f"{now_str}_task_omni_operations_audit_hub.md"
plan_dest_name = f"{now_str}_plan_omni_operations_audit_hub.md"

task_dest = os.path.join(r'C:\AI-BS\Agent_Tasks_History', task_dest_name)
plan_dest = os.path.join(r'C:\AI-BS\Agent_Implementation_Plans_History', plan_dest_name)

shutil.copyfile(task_src, task_dest)
shutil.copyfile(plan_src, plan_dest)
print(f"Archived task to {task_dest}")
print(f"Archived plan to {plan_dest}")

# Append to MASTER_TASKS_CHRONOLOGY.md
tasks_chrono = r'C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md'
with open(tasks_chrono, 'a', encoding='utf-8') as f:
    f.write(f"\n- **{now_str}**: `Agent_Tasks_History/{task_dest_name}` - Omni Operations & Live Audit Hub Implementation (Zero-mock process telemetry, ComfyUI media request tracking, continuous work saves, admin SQLite vault & daemon crash diagnostics)")
print("Updated MASTER_TASKS_CHRONOLOGY.md")

# Append to MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md
plans_chrono = r'C:\AI-BS\MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md'
with open(plans_chrono, 'a', encoding='utf-8') as f:
    f.write(f"\n- **{now_str}**: `Agent_Implementation_Plans_History/{plan_dest_name}` - Architectural Plan: Omni Operations & Live Audit Hub (Zero-mock streaming endpoints, psutil two-phase filtering, ComfyUI output auditing, multi-tenant DB aggregator, log parser)")
print("Updated MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md")
