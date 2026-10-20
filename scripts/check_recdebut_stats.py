import sqlite3
import json
from pathlib import Path

db_path = Path("saved_data/rec_debut.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("Tables:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])

# Check columns of rec_debut_athletes
c.execute("PRAGMA table_info(rec_debut_athletes)")
columns = [r[1] for r in c.fetchall()]
print("Athletes columns:", columns)

total = c.execute("SELECT count(id) FROM rec_debut_athletes").fetchone()[0]
print("Total athletes:", total)

status_counts = c.execute("SELECT status, count(id) FROM rec_debut_athletes GROUP BY status").fetchall()
print("Status counts:", status_counts)

# Pending count
pending_total = c.execute("SELECT count(id) FROM rec_debut_athletes WHERE status='Pending'").fetchone()[0]
print("Pending athletes total:", pending_total)

# Pending with phone
pending_phone = c.execute("SELECT count(id) FROM rec_debut_athletes WHERE status='Pending' AND phone IS NOT NULL AND phone != ''").fetchone()[0]
print("Pending with phone:", pending_phone)

# Pending with email
pending_email = c.execute("SELECT count(id) FROM rec_debut_athletes WHERE status='Pending' AND email IS NOT NULL AND email != ''").fetchone()[0]
print("Pending with email:", pending_email)

# Let's see the campaigns table
print("\nRecent campaigns:")
for camp in c.execute("SELECT id, created_at, sender_id, total_recipients, successful_count, failed_count FROM rec_debut_campaigns ORDER BY id DESC LIMIT 5").fetchall():
    print(camp)

# Show last 10 athletes in the database
last_10 = c.execute("SELECT id, name, phone, email, status FROM rec_debut_athletes ORDER BY id DESC LIMIT 10").fetchall()
print("\nLast 10 athletes (ORDER BY id DESC):")
for a in last_10:
    print(a)

conn.close()
