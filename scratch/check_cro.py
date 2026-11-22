import sqlite3
import os
import json

db_path = r"C:\AI-BS\database\cro_quantitative_ledger.db"
print("DB Exists:", os.path.exists(db_path))

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("\n--- RECENT TRADES ---")
    trades = cur.execute("SELECT * FROM cro_trade_ledger ORDER BY id DESC LIMIT 10").fetchall()
    if trades:
        for t in trades:
            print(dict(t))
    else:
        print("No trades found in cro_trade_ledger.")

    print("\n--- RECENT PRICE SNAPSHOTS ---")
    prices = cur.execute("SELECT * FROM cro_price_history ORDER BY id DESC LIMIT 5").fetchall()
    if prices:
        for p in prices:
            print(dict(p))
    else:
        print("No prices found in cro_price_history.")

ledger_json = r"C:\AI-BS\backend\crypto_ledger.json"
if os.path.exists(ledger_json):
    print("\n--- CRYPTO LEDGER JSON ---")
    with open(ledger_json, "r") as f:
        print(json.dumps(json.load(f), indent=2))
