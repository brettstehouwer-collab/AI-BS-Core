import os
import re
import json
from collections import defaultdict

addresses = defaultdict(lambda: {'occurrences': set(), 'type': 'Unknown'})

patterns = [
    ('EVM (Ethereum / Polygon)', re.compile(r'\b0x[a-fA-F0-9]{40}\b')),
    ('Pearl (PRL)', re.compile(r'\bprl1[a-zA-HJ-NP-Z0-9]{50,65}\b')),
    ('Chia (XCH)', re.compile(r'\bxch1[a-zA-HJ-NP-Z0-9]{50,65}\b')),
    ('Dogecoin (DOGE)', re.compile(r'\bD[5-9A-HJ-NP-U][a-km-zA-HJ-NP-Z1-9]{32,34}\b')),
    ('Bitcoin (BTC)', re.compile(r'\bbc1[a-zA-HJ-NP-Z0-9]{35,62}\b')),
]

known_contracts = {
    '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359': 'USDC Token Contract (Polygon)',
    '0xe60201989b8628f43dc0605f585a72bcf1f1e977': 'CLORE Token Contract (Ethereum)',
    '0xc2132D05D31c914a87C6611C10748AEb04B58e8F': 'USDT Token Contract (Polygon)'
}

target_dirs = [
    r'C:\AI-BS',
    r'C:\AI-BS\backend',
    r'C:\AI-BS\pearl',
    r'C:\AI-BS\docs',
    r'C:\AI-BS\scripts',
    r'C:\AI-BS\Agent_Implementation_Plans_History',
    r'C:\AI-BS\Agent_Tasks_History',
    r'C:\AI-BS\MASTER_KNOWLEDGE_VAULT\03_Agent_Implementation_Plans',
    r'C:\AI-BS\MASTER_KNOWLEDGE_VAULT\04_Agent_Task_History',
    r'C:\AI-BS\MASTER_KNOWLEDGE_VAULT\05_Thinking_Processes_and_Handoffs'
]

for tdir in target_dirs:
    if not os.path.exists(tdir): continue
    for fname in os.listdir(tdir):
        fpath = os.path.join(tdir, fname)
        if os.path.isfile(fpath) and fname.endswith(('.env', '.md', '.json', '.py', '.txt')):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for net_name, pat in patterns:
                        for m in pat.finditer(content):
                            val = m.group(0)
                            if val not in known_contracts:
                                addresses[val]['type'] = net_name
                                addresses[val]['occurrences'].add(fname)
            except: pass

print(f"Total Unique User Wallets Discovered: {len(addresses)}\n")
for addr, meta in sorted(addresses.items(), key=lambda x: len(x[1]['occurrences']), reverse=True):
    print(f"[{meta['type']}] {addr}")
    print(f"  Referenced in: {list(meta['occurrences'])[:3]}")
