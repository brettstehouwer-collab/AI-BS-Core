import sqlite3
import datetime
from pathlib import Path

db_path = Path("saved_data/rec_debut.db")
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

# Overall counts
c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
contacted = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
pending = c.fetchone()[0]

print(f"=== MASTER ROSTER STATUS ===")
print(f"Total Athletes:       {total}")
print(f"Contacted & Verified: {contacted} ({contacted / total * 100:.1f}%)")
print(f"Pending Remaining:    {pending} ({pending / total * 100:.1f}%)")

# Today's dispatches
today_ts = datetime.datetime(2026, 10, 11).timestamp()
c.execute("SELECT COUNT(*), MIN(last_messaged_at), MAX(last_messaged_at) FROM rec_debut_athletes WHERE (status = 'Contacted' OR status = 'Messaged') AND last_messaged_at >= ?", (today_ts,))
today_stat = c.fetchone()
min_t = datetime.datetime.fromtimestamp(today_stat[1]).strftime("%I:%M:%S %p") if today_stat[1] else "N/A"
max_t = datetime.datetime.fromtimestamp(today_stat[2]).strftime("%I:%M:%S %p") if today_stat[2] else "N/A"
print(f"\n=== TODAY'S CELL PHONE TEXT TOTALS ===")
print(f"Total Texts Sent Today: {today_stat[0]}")
print(f"First Sent:             {min_t}")
print(f"Most Recent Sent:       {max_t}")

# Check latest campaigns
c.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count FROM rec_debut_campaigns ORDER BY id DESC LIMIT 5")
print(f"\n=== RECENT CAMPAIGNS IN VAULT ===")
for r in c.fetchall():
    dt = datetime.datetime.fromtimestamp(r[1]).strftime("%I:%M:%S %p") if r[1] else "N/A"
    print(f"Campaign #{r[0]}: Time: {dt} | Sender: {r[2]} | Total: {r[3]} | Sent: {r[4]} | Failed: {r[5]}")

# 10 Most recently messaged athletes from the latest batch
c.execute("SELECT id, name, phone, last_messaged_at, status FROM rec_debut_athletes WHERE status = 'Contacted' ORDER BY last_messaged_at DESC LIMIT 10")
print(f"\n=== LATEST 10 ATHLETES CONTACTED (IN-FLIGHT BATCH) ===")
for r in c.fetchall():
    dt = datetime.datetime.fromtimestamp(r[3]).strftime("%I:%M:%S %p") if r[3] else "N/A"
    print(f" [VERIFIED] ID {r[0]}: {r[1]} | Phone: {r[2]} | Time: {dt} | Status: {r[4]}")

conn.close()
