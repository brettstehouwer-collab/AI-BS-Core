import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

db_path = "C:/AI-BS/database/LLM_CrossCheck_Ledger.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, timestamp, model, prompt, response, score FROM crosscheck_ledger ORDER BY id DESC LIMIT 10;")
    rows = cursor.fetchall()
    
    print(f"=== RECENT BS-CHAT INPUT & REASONING SWARM LOGS ({len(rows)} entries) ===")
    for r in rows:
        rid, ts, model, prompt, resp, score = r
        print(f"\n[Record ID #{rid}] @ {ts}")
        print(f"  • Model: {model}")
        print(f"  • Score: {score}")
        print(f"  • Prompt Snippet: {prompt[:200]}...")
        print(f"  • Response Snippet: {resp[:200]}...")
        print("-" * 60)
        
    conn.close()
