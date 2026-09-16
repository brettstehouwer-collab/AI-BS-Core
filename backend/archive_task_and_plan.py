"""Module to archive tasks and implementation plans into master history."""

import os
import shutil
import time

NOW_STR = time.strftime("%Y%m%d_%H%M%S")
TIMESTAMP_READABLE = time.strftime("%Y-%m-%d %H:%M:%S")

TASK_SRC = (
    r"C:\Users\footb\.gemini\antigravity-ide\brain"
    r"\417997f0-319d-4495-916f-af3a4d4ba4e9\task.md"
)
PLAN_SRC = (
    r"C:\Users\footb\.gemini\antigravity-ide\brain"
    r"\417997f0-319d-4495-916f-af3a4d4ba4e9\implementation_plan.md"
)

TASK_DST_DIR = r"C:\AI-BS\Agent_Tasks_History"
PLAN_DST_DIR = r"C:\AI-BS\Agent_Implementation_Plans_History"

os.makedirs(TASK_DST_DIR, exist_ok=True)
os.makedirs(PLAN_DST_DIR, exist_ok=True)

TASK_DST_FILE = os.path.join(
    TASK_DST_DIR, f"{NOW_STR}_task_automated_syndication_tab.md"
)
PLAN_DST_FILE = os.path.join(
    PLAN_DST_DIR, f"{NOW_STR}_implementation_plan_automated_syndication_tab.md"
)

if os.path.exists(TASK_SRC):
    shutil.copy(TASK_SRC, TASK_DST_FILE)
    print("Archived task:", TASK_DST_FILE)

if os.path.exists(PLAN_SRC):
    shutil.copy(PLAN_SRC, PLAN_DST_FILE)
    print("Archived plan:", PLAN_DST_FILE)

TASKS_CHRONOLOGY = r"C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md"
if os.path.exists(TASKS_CHRONOLOGY):
    with open(TASKS_CHRONOLOGY, "a", encoding="utf-8") as f:
        f_url = TASK_DST_FILE.replace("\\", "/")
        f_base = os.path.basename(TASK_DST_FILE)
        f.write(
            f"\n- **{TIMESTAMP_READABLE}**: [{f_base}](file:///{f_url})"
            f" — Automated Posting & Syndication Tab Integration (v5.126.0)\n"
        )

PLANS_CHRONOLOGY = r"C:\AI-BS\MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md"
if os.path.exists(PLANS_CHRONOLOGY):
    with open(PLANS_CHRONOLOGY, "a", encoding="utf-8") as f:
        f_url = PLAN_DST_FILE.replace("\\", "/")
        f_base = os.path.basename(PLAN_DST_FILE)
        f.write(
            f"\n- **{TIMESTAMP_READABLE}**: [{f_base}](file:///{f_url})"
            f" — Automated Posting & Syndication Tab Implementation Plan"
            f" (v5.126.0)\n"
        )

print("Chronologies updated successfully.")
