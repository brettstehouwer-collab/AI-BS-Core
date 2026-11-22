import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

comp_dir = r"C:\AI-BS\frontend\src\components"
fin_files = [
    'CryptoAccountingTab.jsx',
    'MasterAccountingTab.jsx',
    'UnifiedCryptoHub.jsx',
    'MoneyTrackTab.jsx',
    'DigitalStorefrontTab.jsx',
    'TradingBotTab.jsx',
    'PearlMiningHubTab.jsx'
]

for ff in fin_files:
    fpath = os.path.join(comp_dir, ff)
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        print(f"=== {ff} ({len(content.splitlines())} lines) ===")
        fetches = re.findall(r"fetch\((?:`|'|\")([^`'\"]+)(?:`|'|\")", content)
        print("  Fetches:", set(fetches[:10]))
        
        suspicious = []
        for i, line in enumerate(content.splitlines()):
            lower = line.lower()
            if any(k in lower for k in ['mock', 'dummy', 'fake', 'simulate', '1425', '850.50', '899.99']):
                suspicious.append((i+1, line.strip()))
        print(f"  Suspicious matches: {len(suspicious)}")
        for ln, ls in suspicious[:6]:
            print(f"    Line {ln}: {ls}")
