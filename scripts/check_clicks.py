import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

db_paths = [
    Path(r"C:\AI-BS\saved_data\rec_debut.db"),
    Path(r"C:\Recreational-Debut\saved_data\rec_debut.db")
]

for db in db_paths:
    print(f"\n==================================================")
    print(f"DATABASE: {db}")
    print(f"==================================================")
    if not db.exists():
        print("Does not exist!")
        continue
    conn = sqlite3.connect(str(db))
    c = conn.cursor()

    # Check all tables
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables in DB:", tables)

    # 1. rec_debut_tracking_events
    if "rec_debut_tracking_events" in tables:
        total_events = c.execute("SELECT COUNT(*) FROM rec_debut_tracking_events").fetchone()[0]
        clicks = c.execute("SELECT COUNT(*) FROM rec_debut_tracking_events WHERE UPPER(event_type) = 'CLICK'").fetchone()[0]
        opens = c.execute("SELECT COUNT(*) FROM rec_debut_tracking_events WHERE UPPER(event_type) = 'OPEN'").fetchone()[0]
        print(f"rec_debut_tracking_events: Total={total_events}, Clicks={clicks}, Opens={opens}")
        if clicks > 0:
            print("--- CLICK EVENTS ---")
            for r in c.execute("SELECT id, campaign_id, athlete_id, event_type, target_url, ip_address, created_at FROM rec_debut_tracking_events WHERE UPPER(event_type) = 'CLICK'").fetchall():
                print(" ", r)

    # 2. rec_debut_athletes
    if "rec_debut_athletes" in tables:
        cols = [col[1] for col in c.execute("PRAGMA table_info(rec_debut_athletes)").fetchall()]
        if "click_count" in cols:
            athletes_with_clicks = c.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE click_count > 0").fetchone()[0]
            print(f"rec_debut_athletes with click_count > 0: {athletes_with_clicks}")
            if athletes_with_clicks > 0:
                for r in c.execute("SELECT id, name, phone, click_count, last_clicked_at FROM rec_debut_athletes WHERE click_count > 0").fetchall():
                    print(" ", r)
        else:
            print("Column 'click_count' not in rec_debut_athletes")

    # 3. rec_debut_lead_alerts
    if "rec_debut_lead_alerts" in tables:
        click_alerts = c.execute("SELECT COUNT(*) FROM rec_debut_lead_alerts WHERE UPPER(event_type) = 'CLICK'").fetchone()[0]
        print(f"rec_debut_lead_alerts with event_type='CLICK': {click_alerts}")
        if click_alerts > 0:
            for r in c.execute("SELECT id, athlete_id, athlete_name, event_type, target_url, created_at FROM rec_debut_lead_alerts WHERE UPPER(event_type) = 'CLICK'").fetchall():
                print(" ", r)

    # 4. rec_debut_dispatches
    if "rec_debut_dispatches" in tables:
        total_disp = c.execute("SELECT COUNT(*) FROM rec_debut_dispatches").fetchone()[0]
        cols = [col[1] for col in c.execute("PRAGMA table_info(rec_debut_dispatches)").fetchall()]
        print(f"rec_debut_dispatches total rows: {total_disp}, columns: {cols}")
        if "clicked" in cols:
            clicked_disp = c.execute("SELECT COUNT(*) FROM rec_debut_dispatches WHERE clicked = 1").fetchone()[0]
            print(f"rec_debut_dispatches with clicked=1: {clicked_disp}")

    conn.close()
