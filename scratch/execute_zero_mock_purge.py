import sqlite3

print("=== EXECUTING ZERO-MOCK DATABASE PURGES ===")

# 1. Purge accounting_entries in aibs_master.db and stehouwer_accounting.db
dbs = [
    r"C:\AI-BS\backend\aibs_master.db",
    r"C:\AI-BS\backend\stehouwer_accounting.db"
]

for db_path in dbs:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, date, description, amount FROM accounting_entries WHERE description LIKE '%Test Secondary RTX GPU Rig%'")
        rows = cur.fetchall()
        print(f"Purging {len(rows)} synthetic rows from {os.path.basename(db_path)}: {rows}")
        cur.execute("DELETE FROM accounting_entries WHERE description LIKE '%Test Secondary RTX GPU Rig%'")
        conn.commit()
        remaining = cur.execute("SELECT id, date, description, amount FROM accounting_entries").fetchall()
        print(f"Remaining verified entries in {os.path.basename(db_path)} ({len(remaining)}):")
        for r in remaining:
            print(f"  ID {r[0]} | {r[1]} | {r[2]} | ${r[3]:.2f}")
        conn.close()

# 2. Purge billing_transactions in commercial_usage.db
usage_db = r"C:\AI-BS\backend\commercial_gateway\commercial_usage.db"
if os.path.exists(usage_db):
    conn = sqlite3.connect(usage_db)
    cur = conn.cursor()
    cur.execute("SELECT id, client_name, email, amount_paid FROM billing_transactions WHERE client_name LIKE '%Tester%' OR client_name LIKE '%LiveTestClient%' OR email LIKE '%@paypal.com%' OR email LIKE '%@stripe.com%'")
    rows = cur.fetchall()
    print(f"\nPurging {len(rows)} synthetic billing rows from commercial_usage.db: {rows}")
    cur.execute("DELETE FROM billing_transactions WHERE client_name LIKE '%Tester%' OR client_name LIKE '%LiveTestClient%' OR email LIKE '%@paypal.com%' OR email LIKE '%@stripe.com%'")
    conn.commit()
    remaining = cur.execute("SELECT id, client_name, email, amount_paid FROM billing_transactions").fetchall()
    print(f"Remaining verified billing rows in commercial_usage.db ({len(remaining)}):")
    for r in remaining:
        print(f"  ID {r[0]} | {r[1]} | {r[2]} | ${r[3]:.2f}")
    conn.close()

print("\n=== DATABASE PURGE COMPLETE ===")
