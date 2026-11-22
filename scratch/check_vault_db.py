import sqlite3

conn = sqlite3.connect(r'C:\AI-BS\stehouwer_vault.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]
print('Database tables in stehouwer_vault.db:', tables)

for t in tables:
    if any(k in t.lower() for k in ['wallet', 'crypto', 'address', 'account', 'transfer', 'ledger', 'balance', 'payout']):
        print('Checking table:', t)
        cursor.execute(f"PRAGMA table_info({t});")
        cols = [c[1] for c in cursor.fetchall()]
        print('   Columns:', cols)
        cursor.execute(f"SELECT * FROM {t} LIMIT 5;")
        for row in cursor.fetchall():
            print('   ', row)
