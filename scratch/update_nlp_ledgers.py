import os
import shutil
import datetime

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
date_only = datetime.datetime.now().strftime('%Y%m%d')

def prepend_to_file(filepath, text):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text + '\n\n' + content)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)

def append_to_file(filepath, text):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('\n' + text)

# 1. Update MASTER_TASKS_CHRONOLOGY.md
task_path = r'C:\AI-BS\MASTER_TASKS_CHRONOLOGY.md'
task_entry = f"- **{now}**: Completed NLP Expansion Matrix (spaCy Integration & Multi-Perspective Gauntlet)."
append_to_file(task_path, task_entry)

# 2. Update MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md
plan_path = r'C:\AI-BS\MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md'
plan_entry = f"- **{now}**: Approved NLP Expansion Implementation Plan (Hybrid Parser, Vector Persistence, Generation Gauntlet)."
append_to_file(plan_path, plan_entry)

# 3. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
ledger_update = f"""
### {now} - NLP Core Architecture Expansion (Stehouwer LLM)
**AI Rationale & Implementation:**
- **Goal:** Shift internal narrative processing from raw probabilistic interpretation into a rigid, multi-perspective algorithmic framework based on the 6-Phase NLP Expansion Matrix.
- **Architectural Update:** Injected `AIBSHybridNLPParser` via `spacy` into `backend/aibs_reasoning_engine.py` to flatten narrative syntax into strict dependency structures.
- **Technical Specs:** The `AIBSSelfProblemSolver` now runs prompts through a multi-model Gauntlet (`stehouwer_dolphin` for subjective logic, `stehouwer_qwen` for clinical detachment, `qwen2.5-coder` for technical auditing) before final synthesis. `chroma_storage.py` enriched to strictly store `spacy_root_verbs` and `spacy_entities`.
- **Files Modified:** `C:\\AI-BS\\backend\\aibs_reasoning_engine.py`, `C:\\AI-BS\\backend\\chroma_storage.py`
"""
prepend_to_file(ledger_path, ledger_update)

# 4. Update AI_BS_MASTER_ECOSYSTEM_MANUAL.md
manual_path = r'C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md'
manual_update = f"""
### Update: Core NLP & Reasoning Engine Expansion ({now})
- **Changes:** Upgraded the Stehouwer LLM architecture to utilize `spacy` (en_core_web_trf) for rigid parsing. Inferences now filter through a multi-dimensional perspective Gauntlet (clinical, subjective, technical) before generating the final output.
"""
prepend_to_file(manual_path, manual_update)

artifact_copy = rf'C:\AI-BS\saved_data\artifacts\{date_only}_AI_BS_Master_Ecosystem_Manual.md'
os.makedirs(os.path.dirname(artifact_copy), exist_ok=True)
shutil.copy2(manual_path, artifact_copy)

# 5. Update artifact_history.md
history_path = r'C:\AI-BS\NotebookLM_Records\artifact_history.md'
history_update = f"- **{now}**: Generated {date_only}_AI_BS_Master_Ecosystem_Manual.md (NLP Architecture Expansion)"
if os.path.exists(history_path):
    with open(history_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    lines.insert(2, history_update + '\n')
    with open(history_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

# Archive plans and tasks
os.makedirs(r'C:\AI-BS\Agent_Tasks_History', exist_ok=True)
os.makedirs(r'C:\AI-BS\Agent_Implementation_Plans_History', exist_ok=True)

try:
    shutil.copy2(r'C:\Users\footb\.gemini\antigravity-ide\brain\c2edc56e-50fd-4880-9045-65764320e4b8\task.md', rf'C:\AI-BS\Agent_Tasks_History\task_nlp_expansion_{date_only}.md')
    shutil.copy2(r'C:\Users\footb\.gemini\antigravity-ide\brain\c2edc56e-50fd-4880-9045-65764320e4b8\implementation_plan.md', rf'C:\AI-BS\Agent_Implementation_Plans_History\plan_nlp_expansion_{date_only}.md')
except Exception as e:
    print(f"Archive warning: {{e}}")

print("All ledgers updated, version bumped, and artifacts archived successfully.")
