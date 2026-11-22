with open('C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

for term in ['drip_ledger', 'unreal_assets', 'stehouwer_vault', 'west_michigan', 'clients.db', 'stehouwer_accounting']:
    matches = [m.start() for m in re.finditer(re.escape(term), text, re.IGNORECASE)]
    print(f"=== Matches for {term}: {len(matches)} ===")
    for m in matches[:5]:
        start = max(0, m - 200)
        end = min(len(text), m + 300)
        snippet = text[start:end].replace('\n', ' ')
        print(f"  ... {snippet} ...\n")
