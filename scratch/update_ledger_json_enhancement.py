import os
import datetime
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'a', encoding='utf-8') as f:
    f.write(f'\n\n## {now} - Implemented Gemini JSON Output Enhancements\n')
    f.write('- **Action:** Updated `AI_BS_Swarm_Commander.py` to strip markdown fences and utilize Gemini responseMimeType: application/json.\n')
    f.write('- **Rationale:** Recommended architectural enhancement to ensure cleanly parseable JSON is persisted in the actions DB.\n')
