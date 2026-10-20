import sqlite3
import datetime
from pathlib import Path

db_path = Path("saved_data/rec_debut.db")
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

c.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count FROM rec_debut_campaigns ORDER BY id DESC LIMIT 5")
rows = c.fetchall()
print("=== RECENT CAMPAIGNS IN DB ===")
for r in rows:
    dt = datetime.datetime.fromtimestamp(r[1]).strftime("%Y-%m-%d %H:%M:%S") if r[1] else "N/A"
    print(f"Campaign #{r[0]}: Created {dt} | Sender: {r[2]} | Total: {r[3]} | Success: {r[4]} | Failed: {r[5]}")

today_ts = datetime.datetime(2026, 10, 11).timestamp()
c.execute("SELECT COUNT(*), MIN(last_messaged_at), MAX(last_messaged_at) FROM rec_debut_athletes WHERE (status = 'Contacted' OR status = 'Messaged') AND last_messaged_at >= ?", (today_ts,))
stat = c.fetchone()
print("\n=== TODAY DISPATCH TOTALS ===")
min_t = datetime.datetime.fromtimestamp(stat[1]).strftime("%H:%M:%S") if stat[1] else "N/A"
max_t = datetime.datetime.fromtimestamp(stat[2]).strftime("%H:%M:%S") if stat[2] else "N/A"
print(f"Total Contacted Today: {stat[0]}")
print(f"First Sent Today:      {min_t}")
print(f"Latest Sent Today:     {max_t}")

# Check any recent status changes
c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status = 'Contacted' OR status = 'Messaged'")
total_contacted = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
total_pending = c.fetchone()[0]
print(f"\nOverall Roster Status:")
print(f"Contacted & Verified: {total_contacted} / 2,171 ({total_contacted/2171*100:.1f}%)")
print(f"Pending Remaining:    {total_pending} / 2,171 ({total_pending/2171*100:.1f}%)")

conn.close()
