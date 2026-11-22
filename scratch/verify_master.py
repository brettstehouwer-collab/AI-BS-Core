import sqlite3
import os

conn = sqlite3.connect('C:/AI-BS/backend/aibs_master.db')
conn.execute('PRAGMA wal_checkpoint(TRUNCATE);')
conn.close()

sz = os.path.getsize('C:/AI-BS/backend/aibs_master.db')
print(f'Master DB Size after checkpoint: {sz:,} bytes')

conn = sqlite3.connect('C:/AI-BS/backend/aibs_master.db')
c = conn.cursor()
c.execute("SELECT name, type FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = c.fetchall()
print(f'Total Tables in aibs_master.db: {len(tables)}')
for tbl, _ in tables:
    cnt = c.execute(f'SELECT count(*) FROM "{tbl}"').fetchone()[0]
    # Check client_id column
    c.execute(f'PRAGMA table_info("{tbl}")')
    cols = [col[1] for col in c.fetchall()]
    cid_status = "has client_id" if "client_id" in cols else "NO CLIENT_ID"
    print(f'  {tbl:<28}: {cnt:,} rows ({cid_status})')
conn.close()
