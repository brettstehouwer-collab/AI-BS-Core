import os
import shutil
from datetime import datetime

date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

src_task = r"C:\Users\footb\.gemini\antigravity-ide\brain\87bca6e0-2c75-49be-adf3-634b4c76736d\task.md"
dst_task = rf"C:\AI-BS\Agent_Tasks_History\task_{date_str}.md"

src_plan = r"C:\Users\footb\.gemini\antigravity-ide\brain\87bca6e0-2c75-49be-adf3-634b4c76736d\implementation_plan.md"
dst_plan = rf"C:\AI-BS\Agent_Implementation_Plans_History\plan_{date_str}.md"

if os.path.exists(src_task):
    shutil.copy2(src_task, dst_task)
    print(f"Copied task.md to {dst_task}")
    
if os.path.exists(src_plan):
    shutil.copy2(src_plan, dst_plan)
    print(f"Copied implementation_plan.md to {dst_plan}")
