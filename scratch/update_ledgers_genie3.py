import os
import datetime
import re

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 1. Update task.md
task_path = r'C:\Users\footb\.gemini\antigravity-ide\brain\13dde410-98d2-430d-b734-f6f826438897\task.md'
with open(task_path, 'r', encoding='utf-8') as f:
    task_content = f.read()

task_content = task_content.replace('- `[ ]` Add `world_mutation` column', '- `[x]` Add `world_mutation` column')
task_content = task_content.replace('- `[ ]` Integrate Gemini API support', '- `[x]` Integrate Gemini API support')
task_content = task_content.replace('- `[ ]` Implement `query_genie3_environment`', '- `[x]` Implement `query_genie3_environment`')
task_content = task_content.replace('- `[ ]` Hook new functions into `process_target`', '- `[x]` Hook new functions into `process_target`')

with open(task_path, 'w', encoding='utf-8') as f:
    f.write(task_content)

# 2. Update AI_BS_MASTER_ARCHITECTURAL_LEDGER.md
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'a', encoding='utf-8') as f:
    f.write(f'\n\n## {now} - Phase 18: Genie 3 IPC Bridge & Gemini Fallback\n')
    f.write('- **Action:** Modified `AI_BS_Swarm_Commander.py` to route LLM decisions through a `query_genie3_environment` placeholder (`http://localhost:8888/genie/mutate`). If unreachable, falls back to `query_gemini_fallback` to synthesize environment mutation payloads. Added `world_mutation` column to SQLite `actions.db`.\n')
    f.write('- **Rationale:** User requested Google/Gemini fallback integration for interactive world generation, enabling AI-BS Swarm to trigger dynamic Unreal environment mutations.\n')

# 3. Update AI_BS_MASTER_ECOSYSTEM_MANUAL.md
ecosystem_path = r'C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md'
if os.path.exists(ecosystem_path):
    with open(ecosystem_path, 'r', encoding='utf-8') as f:
        eco_content = f.read()
    
    # Bump version
    version_match = re.search(r'Version: (\d+\.\d+\.\d+)', eco_content)
    if version_match:
        old_version = version_match.group(1)
        parts = old_version.split('.')
        new_version = f"{parts[0]}.{int(parts[1])+1}.0"
        eco_content = eco_content.replace(old_version, new_version)
    
    with open(ecosystem_path, 'w', encoding='utf-8') as f:
        f.write(eco_content)
    
    with open(ecosystem_path, 'a', encoding='utf-8') as f:
        f.write(f'\n\n### Update {now}: Genie 3 Integration\n')
        f.write('The `AI_BS_Swarm_Commander` now supports routing decisions to a Genie 3 API placeholder (`localhost:8888`). If the Genie 3 endpoint is unavailable, it automatically falls back to the Gemini API to hallucinate environmental mutations (weather, lighting, alert levels) via JSON.\n')

print("Ledgers updated.")
