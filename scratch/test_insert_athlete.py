import sqlite3
import time

conn = sqlite3.connect(r"C:\AI-BS\saved_data\rec_debut.db")
c = conn.cursor()
try:
    c.execute("""
        INSERT INTO rec_debut_athletes
        (name, phone, email, sport, high_school, grad_year, city_state, status, notes, team_name, created_at, last_messaged_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Test Athlete", "999-888-7777", "test@gmail.com", "Basketball", "Central High", "2027", "Grand Rapids, MI", "Pending", "Test Notes", "Test Team", time.time(), None
    ))
    conn.commit()
    print("SUCCESS INSERTING TEST ATHLETE, rowid:", c.lastrowid)
    c.execute("DELETE FROM rec_debut_athletes WHERE id = ?", (c.lastrowid,))
    conn.commit()
except Exception as e:
    print("INSERT ERROR:", type(e), e)
conn.close()
