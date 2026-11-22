import os
import shutil
import datetime

now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
now_readable = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

task_src = r'C:\Users\footb\.gemini\antigravity-ide\brain\13dde410-98d2-430d-b734-f6f826438897\task.md'
plan_src = r'C:\Users\footb\.gemini\antigravity-ide\brain\13dde410-98d2-430d-b734-f6f826438897\implementation_plan.md'

task_dest = rf'C:\AI-BS\Agent_Tasks_History\task_genie3_{now}.md'
plan_dest = rf'C:\AI-BS\Agent_Implementation_Plans_History\plan_genie3_{now}.md'

os.makedirs(r'C:\AI-BS\Agent_Tasks_History', exist_ok=True)
os.makedirs(r'C:\AI-BS\Agent_Implementation_Plans_History', exist_ok=True)

if os.path.exists(task_src):
    shutil.copy(task_src, task_dest)
    with open(r'C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md', 'a', encoding='utf-8') as f:
        f.write(f"\n- **{now_readable}**: Archived Genie 3 Integration task list to `{task_dest}`.\n")

if os.path.exists(plan_src):
    shutil.copy(plan_src, plan_dest)
    with open(r'C:\AI-BS\MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md', 'a', encoding='utf-8') as f:
        f.write(f"\n- **{now_readable}**: Archived Genie 3 Integration implementation plan to `{plan_dest}`.\n")

print("Archived successfully.")
