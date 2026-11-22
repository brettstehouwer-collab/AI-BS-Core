import os
import sys
import sqlite3

print("=== CHECKING COMMERCIAL USAGE DB ===")
db_path = r"C:\AI-BS\backend\commercial_gateway\commercial_usage.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in commercial_usage.db:", tables)
    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"Table {t}: {cnt} rows")
        if any(k in t.lower() for k in ["bill", "trans", "pay", "order", "money"]):
            cur.execute(f"SELECT * FROM {t}")
            rows = cur.fetchall()
            print(f"Rows in {t}:", rows)
    conn.close()
else:
    print("commercial_usage.db not found")

print("\n=== CHECKING AIBS_MASTER.DB MONETARY TABLES ===")
master_db = r"C:\AI-BS\database\aibs_master.db"
if os.path.exists(master_db):
    conn = sqlite3.connect(master_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    monetary_tables = [t for t in tables if any(k in t.lower() for k in ["crypto", "account", "trans", "ledger", "tax", "pay", "invoice", "order", "trade", "billing"])]
    print("Monetary tables in aibs_master.db:", monetary_tables)
    for t in monetary_tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"Table {t}: {cnt} rows")
        if cnt > 0:
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            print(f"Sample from {t}:", cur.fetchall())
    conn.close()

print("\n=== CHECKING BACKEND/AIBS_MASTER.DB (IF SEPARATE) ===")
backend_master_db = r"C:\AI-BS\backend\aibs_master.db"
if os.path.exists(backend_master_db):
    conn = sqlite3.connect(backend_master_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    monetary_tables = [t for t in tables if any(k in t.lower() for k in ["crypto", "account", "trans", "ledger", "tax", "pay", "invoice", "order", "trade", "billing"])]
    print("Monetary tables in backend/aibs_master.db:", monetary_tables)
    for t in monetary_tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"Table {t}: {cnt} rows")
        if cnt > 0:
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            print(f"Sample from {t}:", cur.fetchall())
    conn.close()

print("\n=== CHECKING STEHOUWER_ACCOUNTING.DB ===")
steh_acct_db = r"C:\AI-BS\backend\stehouwer_accounting.db"
if os.path.exists(steh_acct_db):
    conn = sqlite3.connect(steh_acct_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in stehouwer_accounting.db:", tables)
    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"Table {t}: {cnt} rows")
        if cnt > 0:
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            print(f"Sample from {t}:", cur.fetchall())
    conn.close()
