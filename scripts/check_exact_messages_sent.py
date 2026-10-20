import sqlite3
import json
from pathlib import Path
from datetime import datetime

conn = sqlite3.connect('saved_data/rec_debut.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
contacted = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_campaigns")
camp_count = c.fetchone()[0]

c.execute("SELECT SUM(successful_count), SUM(failed_count), SUM(total_recipients) FROM rec_debut_campaigns")
sums = c.fetchone()

print(f"=== RECREATIONAL DEBUT MESSAGING TELEMETRY ===")
print(f"Total Athletes in Roster:        {total}")
print(f"Total Contacted & Verified:     {contacted} ({contacted/total*100:.1f}%)")
print(f"Total Pending in Queue:          {total - contacted} ({(total-contacted)/total*100:.1f}%)")
print(f"Total Broadcast Blasts Logged:   {camp_count}")
print(f"Campaign Deliveries Sum:        Successful: {sums[0]} | Failed: {sums[1]} | Total Targeted: {sums[2]}")

print("\n--- CAMPAIGN HISTORY BREAKDOWN ---")
c.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count FROM rec_debut_campaigns ORDER BY id ASC")
for r in c.fetchall():
    dt = datetime.fromtimestamp(r[1]).strftime('%Y-%m-%d %H:%M:%S') if r[1] else 'N/A'
    print(f"  • Campaign #{r[0]}: {dt} | Sender: {r[2]} | Delivered: {r[4]}/{r[3]} | Failed: {r[5]}")

c.execute("SELECT COUNT(*) FROM rec_debut_tracking_events")
events_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athlete_replies")
replies_count = c.fetchone()[0]

print(f"\n--- CLOUDFLARE INBOUND & TRACKING TELEMETRY ---")
print(f"Total Tracking Events (Opens & Clicks via Cloudflare Tunnel): {events_count}")
print(f"Total Inbound Athlete Replies Received:                       {replies_count}")

# Check scheduler state file if it exists
sched_file = Path("saved_data/rec_debut_scheduler_state.json")
if sched_file.exists():
    try:
        sched = json.loads(sched_file.read_text(encoding="utf-8"))
        print("\n--- RECENT SCHEDULER BATCHES ---")
        for b in sched.get("batches", []):
            print(f"  • Batch #{b.get('batch_number')}: {b.get('started_iso')} -> Sent: {b.get('sent')}/{b.get('recipients_targeted')} (Status: {b.get('status')})")
    except Exception as e:
        print(f"Error reading scheduler file: {e}")

# Check latest messaged athlete
c.execute("SELECT id, name, phone, email, last_messaged_at FROM rec_debut_athletes WHERE status = 'Contacted' ORDER BY last_messaged_at DESC LIMIT 5")
print("\n--- 5 MOST RECENT MESSAGES DELIVERED ---")
for r in c.fetchall():
    dt = datetime.fromtimestamp(r[4]).strftime('%Y-%m-%d %H:%M:%S') if r[4] else 'N/A'
    print(f"  • ID {r[0]} | {r[1]} | Phone: {r[2]} | Email: {r[3]} | Timestamp: {dt}")

conn.close()
