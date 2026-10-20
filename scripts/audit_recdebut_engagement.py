import sqlite3

conn = sqlite3.connect(r'C:\AI-BS\saved_data\rec_debut.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])

c.execute("PRAGMA table_info(rec_debut_athletes)")
cols = [r[1] for r in c.fetchall()]
print("Athlete columns:", cols)

# Check athletes with engagement
c.execute("SELECT id, name, phone, email, open_count, click_count, last_opened_at, last_clicked_at, status FROM rec_debut_athletes WHERE open_count > 0 OR click_count > 0")
engaged = c.fetchall()
print(f"Total engaged athletes: {len(engaged)}")
for row in engaged:
    print(" ", row)

# Check tracking logs
if "rec_debut_tracking_events" in [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    c.execute("SELECT COUNT(*) FROM rec_debut_tracking_events")
    print("Tracking events count:", c.fetchone()[0])
    c.execute("SELECT * FROM rec_debut_tracking_events ORDER BY id DESC LIMIT 10")
    for r in c.fetchall():
        print("  Event:", r)

# Check athlete replies
if "rec_debut_replies" in [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    c.execute("SELECT COUNT(*) FROM rec_debut_replies")
    print("Replies count:", c.fetchone()[0])
    c.execute("SELECT * FROM rec_debut_replies ORDER BY id DESC LIMIT 10")
    for r in c.fetchall():
        print("  Reply:", r)

# Check campaign summary
c.execute("SELECT id, created_at, total_recipients, successful_count, failed_count FROM rec_debut_campaigns ORDER BY id DESC LIMIT 10")
print("Campaigns:")
for camp in c.fetchall():
    print(" ", camp)
