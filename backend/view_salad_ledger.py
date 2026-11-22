import sqlite3
import pandas as pd

DB_PATH = r'C:\AI-BS\backend\stehouwer_vault.db'

def view_ledger():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM salad_job_ledger ORDER BY id DESC LIMIT 50", conn)
        if df.empty:
            print("Ledger is currently empty. Waiting for the first Salad job to complete...")
        else:
            print("=== AI-BS Salad Job Ledger (God-Mode) ===")
            print(df.to_string(index=False))
    except Exception as e:
        print(f"Error reading ledger: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    view_ledger()
