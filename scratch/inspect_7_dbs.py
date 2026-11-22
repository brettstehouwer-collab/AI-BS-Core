import sqlite3
import os

dbs = [
    'C:/AI-BS/backend/state.db',
    'C:/AI-BS/backend/clients.db',
    'C:/AI-BS/backend/unreal_assets.db',
    'C:/AI-BS/backend/stehouwer_vault.db',
    'C:/AI-BS/backend/stehouwer_accounting.db',
    'C:/AI-BS/backend/west_michigan.db',
    'C:/AI-BS/backend/drip_ledger.db'
]

for db in dbs:
    name = os.path.basename(db)
    if not os.path.exists(db):
        print(f'{name}: DOES NOT EXIST')
        continue
    sz = os.path.getsize(db)
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'")
    items = c.fetchall()
    print(f'=== {name} ({sz:,} bytes) ===')
    for tbl, typ, sql in items:
        try:
            cnt = c.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
            print(f'  [{typ.upper()}] {tbl}: {cnt:,} rows')
        except Exception as e:
            print(f'  [{typ.upper()}] {tbl}: err ({e})')
    conn.close()
    print()
