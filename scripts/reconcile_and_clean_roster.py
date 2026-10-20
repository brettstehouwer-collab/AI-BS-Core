import sqlite3
import csv
import json
import os
import re

db_path = r"C:\AI-BS\saved_data\rec_debut.db"
csv_raw_path = r"C:\Users\footb\OneDrive\Desktop\Athletes_Nike_Recruiting_Guide.csv"
csv_clean_path = r"C:\Users\footb\OneDrive\Desktop\Athletes_Nike_Recruiting_Guide_Cleaned.csv"
csv_phone_only_path = r"C:\Users\footb\OneDrive\Desktop\Athletes_Nike_Phone_Only_Roster.csv"
teams_archive_path = r"C:\AI-BS\saved_data\rec_debut_teams_archive.json"
master_csv_path = r"C:\AI-BS\saved_data\rec_debut_athlete_emails_master.csv"
master_json_path = r"C:\AI-BS\saved_data\rec_debut_athlete_emails.json"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
ARTIFACT_NAMES = {"ADDRESS", "ATHLETE NAME", "COACH NAME", "COACH NAME ADDRESS", "COACHNAME ADDRESS", "YEAR ATHLETE NAME"}

def run_scrub_and_clean():
    print("=== STARTING ROSTER RECONCILIATION & SCRUBBING ===")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Inspect current state in DB
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    initial_total = cur.fetchone()[0]
    print(f"Initial rec_debut_athletes rows: {initial_total}")

    # 2. Identify OCR Artifacts in DB
    cur.execute("SELECT id, name, phone, email, notes, team_name FROM rec_debut_athletes")
    all_rows = cur.fetchall()

    artifact_ids = []
    blank_team_ids = []
    blank_teams_data = []
    phone_only_ids = []

    for r in all_rows:
        aid, name, phone, email, notes, team = r
        name_clean = (name or "").strip()
        phone_clean = (phone or "").strip()
        email_clean = (email or "").strip()

        if name_clean.upper() in ARTIFACT_NAMES:
            artifact_ids.append(aid)
        elif not email_clean and not phone_clean:
            blank_team_ids.append(aid)
            blank_teams_data.append({
                "id": aid,
                "name": name_clean,
                "team_name": team,
                "notes": notes
            })
        elif not email_clean and phone_clean:
            phone_only_ids.append(aid)

    print(f"Identified {len(artifact_ids)} OCR header artifacts in DB.")
    print(f"Identified {len(blank_team_ids)} blank team placeholder rows in DB.")
    print(f"Identified {len(phone_only_ids)} phone-only athletes in DB.")

    # 3. Archive blank team placeholders
    with open(teams_archive_path, "w", encoding="utf-8") as f:
        json.dump(blank_teams_data, f, indent=2)
    print(f"Archived {len(blank_teams_data)} team placeholder records to {teams_archive_path}")

    # 4. Purge artifacts and blank team rows from rec_debut_athletes
    purge_ids = artifact_ids + blank_team_ids
    if purge_ids:
        placeholders = ",".join(["?"] * len(purge_ids))
        cur.execute(f"DELETE FROM rec_debut_athletes WHERE id IN ({placeholders})", purge_ids)
        conn.commit()
        print(f"Purged {len(purge_ids)} non-athlete rows from rec_debut_athletes.")

    # 5. Tag and preserve phone-only athletes
    if phone_only_ids:
        placeholders = ",".join(["?"] * len(phone_only_ids))
        cur.execute(f"""
            UPDATE rec_debut_athletes
            SET email_status = 'NO_EMAIL',
                notes = CASE 
                    WHEN notes LIKE '%[Phone Only%' THEN notes 
                    ELSE COALESCE(notes, '') || ' | [Phone Only - Requires Direct 1-on-1 SMS/Call]' 
                END
            WHERE id IN ({placeholders})
        """, phone_only_ids)
        conn.commit()
        print(f"Updated {len(phone_only_ids)} phone-only athletes with email_status='NO_EMAIL' and direct-reach notes.")

    # 6. Verify new DB totals
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    new_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email IS NOT NULL AND email != ''")
    email_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE email_status = 'NO_EMAIL'")
    phone_only_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rec_debut_athletes WHERE status IS NULL OR status = 'Pending' OR status = 'Selected'")
    pending_count = cur.fetchone()[0]

    print("\n--- Updated rec_debut_athletes Table Stats ---")
    print(f"Total Athletes: {new_total}")
    print(f"Athletes with Valid Email: {email_count}")
    print(f"Phone-Only Athletes (Preserved): {phone_only_count}")
    print(f"Pending Outreach Candidates: {pending_count}")

    # 7. Clean and Export the CSVs from Athletes_Nike_Recruiting_Guide.csv
    print(f"\nProcessing {csv_raw_path}...")
    cleaned_nike_athletes = []
    phone_only_nike_athletes = []

    with open(csv_raw_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip()
            phone = (row.get("phone") or "").strip()

            # Skip header artifacts and blank teams
            if name.upper() in ARTIFACT_NAMES:
                continue
            if not email and not phone:
                continue

            # Split name into first and last
            parts = name.split(None, 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

            athlete_dict = {
                "first_name": first_name,
                "last_name": last_name,
                "name": name,
                "email": email,
                "phone": phone,
                "grad_year": row.get("grad_year", ""),
                "height": row.get("height", ""),
                "jersey": row.get("jersey", ""),
                "school": row.get("school", ""),
                "team": row.get("team", ""),
                "high_school_coach": row.get("high_school_coach", ""),
                "high_school_coach_phone": row.get("high_school_coach_phone", ""),
                "page": row.get("page", "")
            }

            if email and EMAIL_REGEX.match(email):
                cleaned_nike_athletes.append(athlete_dict)
            elif phone:
                phone_only_nike_athletes.append(athlete_dict)

    print(f"Cleaned Nike Guide Athletes with Email: {len(cleaned_nike_athletes)}")
    print(f"Cleaned Nike Guide Phone-Only Athletes: {len(phone_only_nike_athletes)}")

    # Write Athletes_Nike_Recruiting_Guide_Cleaned.csv
    fieldnames = ["first_name", "last_name", "name", "email", "phone", "grad_year", "height", "jersey", "school", "team", "high_school_coach", "high_school_coach_phone", "page"]
    with open(csv_clean_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_nike_athletes)
    print(f"Saved cleaned email roster to: {csv_clean_path} ({len(cleaned_nike_athletes)} rows)")

    # Write Athletes_Nike_Phone_Only_Roster.csv
    with open(csv_phone_only_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(phone_only_nike_athletes)
    print(f"Saved phone-only roster to: {csv_phone_only_path} ({len(phone_only_nike_athletes)} rows)")

    # 8. Synchronize Master JSON and CSV in saved_data
    cur.execute("""
        SELECT id, name, phone, email, sport, high_school, grad_year, city_state, team_name, notes
        FROM rec_debut_athletes
        WHERE email IS NOT NULL AND email != ''
        ORDER BY id ASC
    """)
    db_email_athletes = cur.fetchall()

    master_list = []
    for row in db_email_athletes:
        aid, name, phone, email, sport, hs, grad, city_state, team, notes = row
        parts = (name or "").split(None, 1)
        fn = parts[0] if parts else ""
        master_list.append({
            "id": aid,
            "name": name,
            "first_name": fn,
            "email": email,
            "phone": phone,
            "sport": sport or "Basketball",
            "high_school": hs or "",
            "grad_year": grad or "",
            "city_state": city_state or "",
            "team": team or "",
            "notes": notes or "",
            "source": "rec_debut_master"
        })

    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(master_list, f, indent=2)
    print(f"Updated {master_json_path} with {len(master_list)} master email athletes.")

    master_fields = ["id", "name", "first_name", "email", "phone", "sport", "high_school", "grad_year", "city_state", "team", "notes", "source"]
    with open(master_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=master_fields)
        writer.writeheader()
        writer.writerows(master_list)
    print(f"Updated {master_csv_path} with {len(master_list)} master email athletes.")

    conn.close()
    print("=== RECONCILIATION & SCRUBBING COMPLETE ===")

if __name__ == "__main__":
    run_scrub_and_clean()
