import os
import re
import json

results = {
    'potential_leaks': [],
    'zero_mock_audit': {
        'suspicious_mock_balances': []
    },
    'safety_filter_audit': {},
    'multi_tenant_compliance': {
        'total_db_tables_checked': 0,
        'tables_missing_client_id': []
    }
}

# 1. Regex scan for secrets
secret_patterns = [
    (r'(?:sk-[a-zA-Z0-9]{20,})', 'OpenAI/Anthropic Secret Key Pattern'),
    (r'(?:AIza[0-9A-Za-z-_]{35})', 'Google API Key Pattern'),
    (r'(?:ghp_[a-zA-Z0-9]{36})', 'GitHub Personal Access Token'),
    (r'(?:xox[baprs]-[0-9a-zA-Z]{10,48})', 'Slack Token Pattern'),
    (r'(?:[1-9A-HJ-NP-Za-km-z]{44,88})', 'Solana/Crypto Private Key Base58 (raw)'),
]

# Scan code and config files
scanned_extensions = ['.py', '.env', '.json', '.bat', '.ps1', '.sh', '.js', '.jsx', '.ts', '.tsx']
ignore_dirs = ['node_modules', '.git', 'pyppeteer_env', 'Android Studio', 'scratch', 'dist', 'dist-electron']

for root, dirs, files in os.walk(r'C:\AI-BS'):
    if any(ig in root for ig in ignore_dirs):
        continue
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in scanned_extensions and not f.endswith('lock.json') and not f.endswith('manifest.json') and f != 'symbol_graph.json':
            p = os.path.join(root, f)
            rel = os.path.relpath(p, r'C:\AI-BS')
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as sf:
                    content = sf.read()
                for pat, label in secret_patterns:
                    # Skip matching firebase client keys if they are just standard web config
                    matches = re.findall(pat, content)
                    if matches:
                        for m in matches:
                            if 'AIza' in m and ('firebase' in rel.lower() or 'firebase.js' in rel):
                                continue # standard public web client api key
                            if 'your_key' in m.lower() or 'dummy' in m.lower() or 'placeholder' in m.lower() or 'fake' in m.lower():
                                continue
                            results['potential_leaks'].append({
                                'file': rel,
                                'type': label,
                                'snippet': m[:6] + '...' + m[-4:]
                            })
            except Exception:
                pass

# 2. Zero-Mock Real Money & Fiscal Tax Accounting Rule check
# Check CryptoAccountingTab, MasterAccountingTab, and financial databases
accounting_files = [
    r'C:\AI-BS\frontend\src\components\CryptoAccountingTab.jsx',
    r'C:\AI-BS\frontend\src\components\MasterAccountingTab.jsx',
    r'C:\AI-BS\backend\routers\crypto_router.py'
]
for af in accounting_files:
    if os.path.exists(af):
        with open(af, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
        rel = os.path.relpath(af, r'C:\AI-BS')
        # Check if there are hardcoded fake transactions like [ { amount: 1000, tx: "mock" } ]
        mock_matches = re.findall(r'(?:mock_transactions|fake_balance|sample_crypto|dummy_transfer)', c, re.IGNORECASE)
        if mock_matches:
            results['zero_mock_audit']['suspicious_mock_balances'].append({'file': rel, 'matches': mock_matches})

# 3. Stehouwer LLM Safety Filter Directive
# Check system instruction/safety files for S1, S3, S4
backend_safety = r'C:\AI-BS\backend\core\hybrid_reasoning_engine.py'
if os.path.exists(backend_safety):
    with open(backend_safety, 'r', encoding='utf-8', errors='ignore') as f:
        sc = f.read()
    results['safety_filter_audit'] = {
        'has_S1': 'S1' in sc,
        'has_S3': 'S3' in sc,
        'has_S4': 'S4' in sc,
        's4_locked': 'S4' in sc and 'Child Sexual Exploitation' in sc
    }

with open(r'C:\AI-BS\scratch\phase6_security_audit_results.json', 'w', encoding='utf-8') as out:
    json.dump(results, out, indent=2)

print('Phase 6 Security Audit script complete!')
