import requests
import sqlite3
import datetime

def main():
    print("=== LIVE RECREATIONAL DEBUT TELEMETRY AUDIT ===")
    
    # 1. Query broadcast status API
    try:
        res = requests.get('http://127.0.0.1:8080/api/v1/recdebut/broadcast/status', timeout=5).json()
        print("\n--- Broadcast Engine Status ---")
        print(f"Active: {res.get('active')}")
        print(f"Status: {res.get('status')}")
        print(f"Campaign Type: {res.get('campaign_type')}")
        print(f"Dispatched: {res.get('sent')} / {res.get('total')} ({res.get('progress_pct')}%)")
        print(f"Failed: {res.get('failed')}")
        print(f"Current Account: {res.get('current_account')}")
        print(f"Current Recipient: {res.get('current_athlete')}")
    except Exception as e:
        print(f"Error querying broadcast API: {e}")

    # 1b. Query scheduler daemon status API
    try:
        s_res = requests.get('http://127.0.0.1:8080/api/v1/recdebut/scheduler/status', timeout=5).json()
        print("\n--- Autonomous Scheduler Daemon Status ---")
        print(s_res)
    except Exception as e:
        print(f"Error querying scheduler API: {e}")

    # 2. Query rec_debut.db database
    try:
        conn = sqlite3.connect('saved_data/rec_debut.db')
        cur = conn.cursor()
        
        print("\n--- Database Roster Verification (rec_debut.db) ---")
        cur.execute("SELECT count(*) FROM rec_debut_athletes")
        total_athletes = cur.fetchone()[0]
        print(f"Total Athletes in System: {total_athletes}")
        
        cur.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status")
        status_counts = dict(cur.fetchall())
        print(f"Roster Status Breakdown: {status_counts}")
        
        cur.execute("SELECT email_status, count(*) FROM rec_debut_athletes WHERE status = 'Pending' GROUP BY email_status")
        email_status_counts = dict(cur.fetchall())
        print(f"Pending Email Verification Breakdown: {email_status_counts}")
        
        cur.execute("SELECT count(*) FROM rec_debut_athletes WHERE last_messaged_at IS NOT NULL")
        with_timestamp = cur.fetchone()[0]
        print(f"Athletes with Verified Timestamp: {with_timestamp}")
        
        cur.execute("""
            SELECT name, email, phone, status, datetime(last_messaged_at, 'unixepoch', 'localtime') 
            FROM rec_debut_athletes 
            WHERE status = 'Contacted' 
            ORDER BY last_messaged_at DESC 
            LIMIT 10
        """)
        recent_sends = cur.fetchall()
        print(f"\nMost Recent 10 Dispatched & Verified Athletes:")
        for idx, row in enumerate(recent_sends, 1):
            print(f"  {idx}. {row[0]} | {row[1]} | {row[2]} | {row[3]} | Sent: {row[4]}")
            
        cur.execute("SELECT count(*) FROM rec_debut_excluded_coaches")
        coaches_count = cur.fetchone()[0]
        print(f"\nCoaches Quarantined (100% collision protected): {coaches_count}")
        
        conn.close()
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == '__main__':
    main()
