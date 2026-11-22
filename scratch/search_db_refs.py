import os

dbs = [
    'state.db',
    'clients.db',
    'unreal_assets.db',
    'stehouwer_vault.db',
    'stehouwer_accounting.db',
    'west_michigan.db',
    'drip_ledger.db'
]

results = {db: [] for db in dbs}

search_roots = ['C:/AI-BS/backend', 'C:/AI-BS/frontend/src', 'C:/AI-BS/frontend/components']

for sroot in search_roots:
    for root, dirs, files in os.walk(sroot):
        norm = root.replace('\\', '/')
        if any(x in norm for x in ['node_modules', '.git', '.venv', 'dist', 'build', 'saved_data', '__pycache__', 'backup']):
            continue
        for f in files:
            if f.endswith(('.py', '.js', '.jsx')):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fl:
                        content = fl.read()
                        for db in dbs:
                            if db in content:
                                results[db].append(path.replace('\\', '/'))
                except Exception:
                    pass

for db, files in results.items():
    print(f"=== {db} (used in {len(files)} files) ===")
    for f in sorted(files):
        print(f"  {f}")
    print()
