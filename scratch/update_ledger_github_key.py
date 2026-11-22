import os
import datetime
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
ledger_path = r'C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md'
with open(ledger_path, 'a', encoding='utf-8') as f:
    f.write(f'\n\n## {now} - Created .github directory and saved secret key\n')
    f.write('- **Action:** Created `C:\\AI-BS\\.github\\secret_key.txt` and securely saved the provided GitHub token into it.\n')
    f.write('- **Rationale:** Stored GitHub secret keys logically separated in a `.github` folder based on user request.\n')
