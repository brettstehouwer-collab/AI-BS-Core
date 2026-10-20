import sqlite3
import os
import csv
import json

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
csv_path = r"C:\Users\footb\OneDrive\Desktop\Athletes_Nike_Recruiting_Guide.csv"

print("--- Checking rec_debut.db ---")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)

    for tbl in tables:
        cur.execute(f"PRAGMA table_info({tbl})")
        cols = [c[1] for c in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        print(f"Table '{tbl}': {cnt} rows, cols: {cols}")

    if "rec_debut_athletes" in tables:
        cur.execute("SELECT status, count(*) FROM rec_debut_athletes GROUP BY status")
        print("Status breakdown in rec_debut_athletes:", cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email IS NOT NULL AND email != ''")
        print("Athletes with non-empty email:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE phone IS NOT NULL AND phone != ''")
        print("Athletes with non-empty phone:", cur.fetchone()[0])

        cur.execute("SELECT id, name, phone, email, status FROM rec_debut_athletes LIMIT 5")
        print("Sample 5 athletes:", cur.fetchall())
    conn.close()
else:
    print("rec_debut.db not found!")

print("\n--- Detailed Audit of Athletes_Nike_Recruiting_Guide.csv ---")
if os.path.exists(csv_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows in CSV: {len(rows)}")
    valid_email_rows = []
    phone_only_rows = []
    blank_both_rows = []
    header_artifact_rows = []

    import re
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    for idx, r in enumerate(rows, 1):
        name = (r.get("name") or "").strip()
        email_val = (r.get("email") or "").strip()
        phone_val = (r.get("phone") or "").strip()

        # Check if header artifact
        if any(bad in name.upper() for bad in ["COACH NAME", "ADDRESS", "EMAIL PHONE", "ATHLETE NAME", "YEAR ATHLETE"]):
            header_artifact_rows.append((idx, r))
        elif email_val and EMAIL_REGEX.match(email_val):
            valid_email_rows.append((idx, r))
        elif phone_val and not email_val:
            phone_only_rows.append((idx, r))
        else:
            blank_both_rows.append((idx, r))

    print(f"Valid Emails: {len(valid_email_rows)}")
    print(f"Phone-only Athletes: {len(phone_only_rows)}")
    print(f"Blank both (teams/formatting): {len(blank_both_rows)}")
    print(f"Header artifacts: {len(header_artifact_rows)}")
    print(f"Total flagged (invalid/missing emails): {len(phone_only_rows) + len(blank_both_rows) + len(header_artifact_rows)}")

    print("\nHeader artifacts found:")
    for idx, r in header_artifact_rows:
        print(f"  Row {idx}: name='{r.get('name')}', email='{r.get('email')}', phone='{r.get('phone')}'")

    print(f"\nPhone-only athletes (first 10 of {len(phone_only_rows)}):")
    for idx, r in phone_only_rows[:10]:
        print(f"  Row {idx}: name='{r.get('name')}', phone='{r.get('phone')}', school='{r.get('school')}'")

    print(f"\nBlank both sample (first 10 of {len(blank_both_rows)}):")
    for idx, r in blank_both_rows[:10]:
        print(f"  Row {idx}: name='{r.get('name')}', team='{r.get('team')}'")

    # Now let's check how many of these exist in rec_debut_athletes
    cur.execute("SELECT name, phone, email, status FROM rec_debut_athletes")
    db_athletes = cur.fetchall()
    db_phones = {a[1]: a for a in db_athletes if a[1]}
    db_emails = {a[2].lower(): a for a in db_athletes if a[2]}
    db_names = {a[0].lower(): a for a in db_athletes if a[0]}

    matched_by_email = sum(1 for _, r in valid_email_rows if r.get("email", "").strip().lower() in db_emails)
    print(f"\nOf the {len(valid_email_rows)} valid email rows in CSV, how many are in rec_debut_athletes by email? {matched_by_email}")
    
    # Check if header artifacts exist in rec_debut_athletes
    found_artifacts_in_db = [a for a in db_athletes if any(bad in (a[0] or "").upper() for bad in ["COACH NAME", "ADDRESS", "EMAIL PHONE", "ATHLETE NAME"])]
    print(f"Header artifacts currently in rec_debut_athletes table: {len(found_artifacts_in_db)}")
    for a in found_artifacts_in_db:
        print("  In DB:", a)

    print("\n--- Checking the 18 phone-only athletes with normalized phone ---")
    for idx, r in phone_only_rows:
        name = r.get("name", "").strip()
        raw_phone = r.get("phone", "").strip()
        digits = "".join(filter(str.isdigit, raw_phone))
        e164 = f"+1{digits}" if len(digits) == 10 else f"+{digits}"
        cur.execute("SELECT id, name, phone, email, status, notes FROM rec_debut_athletes WHERE phone = ? OR phone = ? OR name LIKE ?", (e164, raw_phone, f"%{name}%"))
        matches = cur.fetchall()
        print(f"Row {idx} ({name}, {raw_phone} -> {e164}): found in DB -> {matches}")

    conn.close()



