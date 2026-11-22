import os
import datetime
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'a', encoding='utf-8') as f:
    f.write(f'\n\n## {now} - Installed google-antigravity-sdk skill\n')
    f.write('- **Action:** Installed `google-antigravity-sdk` globally via Vercel skills CLI.\n')
    f.write('- **Rationale:** Provided the agent with documentation and core capabilities for building AI agents with the Antigravity SDK.\n')
