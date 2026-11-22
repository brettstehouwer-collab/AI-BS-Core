import os
import re
import json
from collections import defaultdict

addresses = defaultdict(lambda: {'occurrences': set(), 'labels': set(), 'type': 'Unknown'})

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

for root, dirs, files in os.walk(r'C:\AI-BS'):
    if any(x in root for x in ['node_modules', '.git', 'venv', 'pyppeteer_env', 'ComfyUI', 'dist', 'build']):
        continue
    for file in files:
        if file.endswith(('.env', '.json', '.md', '.py', '.txt', '.bat', '.ps1')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for net_name, pat in patterns:
                        for match in pat.finditer(content):
                            addr = match.group(0)
                            addresses[addr]['type'] = net_name
                            rel_path = os.path.relpath(path, r'C:\AI-BS')
                            addresses[addr]['occurrences'].add(rel_path)
                            start = max(0, match.start() - 80)
                            end = min(len(content), match.end() + 80)
                            snippet = content[start:end].replace('\n', ' ')
                            for keyword in ['treasury', 'payout', 'destination', 'cryptocom', 'sofi', 'herominers', 'hot wallet', 'cold', 'safetrade', 'wallet', 'deposit', 'xch', 'doge', 'clore', 'bitcoin', 'pearl']:
                                if keyword in snippet.lower():
                                    addresses[addr]['labels'].add(keyword)
            except: pass

print(f"Total Unique Cryptocurrency Addresses Scanned: {len(addresses)}\n")

# Filter out contracts
results = []
for addr, data in addresses.items():
    is_contract = addr in known_contracts
    results.append({
        'address': addr,
        'type': data['type'],
        'is_contract': is_contract,
        'contract_name': known_contracts.get(addr),
        'file_count': len(data['occurrences']),
        'sample_files': list(data['occurrences'])[:4],
        'context_labels': list(data['labels'])
    })

# Sort by file count descending
results.sort(key=lambda x: x['file_count'], reverse=True)

with open(r'C:\AI-BS\scratch\wallet_audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)

for r in results:
    if r['is_contract']:
        print(f"[TOKEN CONTRACT] {r['address']} -> {r['contract_name']}")
    elif r['file_count'] > 1 or r['type'] != 'EVM (Ethereum / Polygon)':
        print(f"[{r['type']}] {r['address']} (Found in {r['file_count']} files)")
        print(f"   Context: {', '.join(r['context_labels'])}")
        print(f"   Files: {', '.join(r['sample_files'][:2])}")
        print("-" * 60)
