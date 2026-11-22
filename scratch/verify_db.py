import sqlite3

db_path = r"C:\AI-BS\backend\aibs_master.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='crypto_transfers'")
schema = c.fetchone()
print("SCHEMA FOUND:", bool(schema))
if schema:
    print(schema[0])

c.execute("SELECT count(*), COALESCE(sum(amount), 0) FROM crypto_transfers")
row = c.fetchone()
print("ROWS COUNT:", row[0], "TOTAL AMOUNT:", row[1])

c.execute("SELECT id, date, source_account, dest_account, asset, amount, category FROM crypto_transfers LIMIT 5")
for r in c.fetchall():
    print("ENTRY:", r)

conn.close()
