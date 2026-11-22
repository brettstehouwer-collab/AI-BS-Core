import sqlite3

db_path = r"C:\AI-BS\backend\aibs_master.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("UPDATE crypto_transfers SET dest_account = 'Crypto.com Polygon Deposit (0x4761...)' WHERE dest_account LIKE '%0xaDEE%'")
if c.rowcount > 0:
    print(f"Updated {c.rowcount} row(s) in aibs_master.db")
conn.commit()
conn.close()

# Also check stehouwer_accounting.db if it exists
import os
acc_db = r"C:\AI-BS\backend\stehouwer_accounting.db"
if os.path.exists(acc_db):
    conn = sqlite3.connect(acc_db)
    c = conn.cursor()
    try:
        c.execute("UPDATE crypto_transfers SET dest_account = 'Crypto.com Polygon Deposit (0x4761...)' WHERE dest_account LIKE '%0xaDEE%'")
        if c.rowcount > 0:
            print(f"Updated {c.rowcount} row(s) in stehouwer_accounting.db")
        conn.commit()
    except Exception as e:
        print("stehouwer_accounting.db notice:", e)
    conn.close()
