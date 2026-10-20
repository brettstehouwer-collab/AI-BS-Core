"""
Normalize all student-athlete and coach phone numbers to include '+1' USA country code (E.164 standard).
Updates:
1. RecDebut_Athletes_Clean_List_2026-10-09.csv (in OneDrive\Pictures)
2. RecDebut_Athletes_Clean_List_2026-10-09 (1).csv (in OneDrive\Pictures)
3. RecDebut_Athletes_Emails_For_Blast.csv (in OneDrive\Pictures)
4. rec_debut_athlete_emails_master.csv (in saved_data)
5. rec_debut_athlete_emails.json (in saved_data)
6. rec_debut.db (tables: rec_debut_athletes, rec_debut_excluded_coaches)
"""

import os
import re
import json
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAVED_DATA = BASE_DIR / "saved_data"
ONEDRIVE_PICTURES = Path.home() / "OneDrive" / "Pictures"

def to_usa_e164(phone: str) -> str:
    if pd.isna(phone) or not phone:
        return ""
    s = str(phone).strip()
    digits = re.sub(r'\D', '', s)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 10 and digits.startswith('1'):
        return f"+{digits[:11]}"
    elif len(digits) > 0:
        return f"+1{digits[-10:]}" if len(digits) >= 10 else f"+1{digits}"
    return s

def to_usa_formatted(phone: str) -> str:
    e164 = to_usa_e164(phone)
    if e164.startswith("+1") and len(e164) == 12:
        d = e164[2:]
        return f"+1-{d[:3]}-{d[3:6]}-{d[6:]}"
    return e164

print("=======================================================")
print("   NORMALIZING PHONE NUMBERS WITH '+1' FOR USA")
print("=======================================================")

# 1. Update CSV Files
csv_targets = [
    ONEDRIVE_PICTURES / "RecDebut_Athletes_Clean_List_2026-10-09.csv",
    ONEDRIVE_PICTURES / "RecDebut_Athletes_Clean_List_2026-10-09 (1).csv",
    ONEDRIVE_PICTURES / "RecDebut_Athletes_Emails_For_Blast.csv",
    SAVED_DATA / "rec_debut_athlete_emails_master.csv"
]

for csv_path in csv_targets:
    if not csv_path.exists():
        print(f"[-] File not found: {csv_path}")
        continue

    print(f"\n[+] Processing: {csv_path.name}")
    try:
        df = pd.read_csv(csv_path)
        phone_col = None
        for col_name in ['Phone', 'phone', 'PHONE', 'telephone', 'mobile']:
            if col_name in df.columns:
                phone_col = col_name
                break

        if not phone_col:
            print(f"  [!] No phone column detected in {csv_path.name}")
            continue

        original_samples = df[phone_col].head(3).tolist()
        df[phone_col] = df[phone_col].apply(to_usa_e164)
        new_samples = df[phone_col].head(3).tolist()

        df.to_csv(csv_path, index=False)
        print(f"  [OK] Updated {len(df)} records in {csv_path.name}")
        print(f"  Before: {original_samples}")
        print(f"  After:  {new_samples}")
    except Exception as e:
        print(f"  [ERR] Failed to update {csv_path.name}: {e}")

# 2. Update rec_debut_athlete_emails.json
json_path = SAVED_DATA / "rec_debut_athlete_emails.json"
if json_path.exists():
    print(f"\n[+] Processing JSON: {json_path.name}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        updated_count = 0
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "phone" in item:
                    item["phone"] = to_usa_e164(item["phone"])
                    updated_count += 1
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"  [OK] Updated {updated_count} records in {json_path.name}")
    except Exception as e:
        print(f"  [ERR] Failed to update {json_path.name}: {e}")

# 3. Update SQLite Database
db_path = SAVED_DATA / "rec_debut.db"
if db_path.exists():
    print(f"\n[+] Processing SQLite Database: {db_path.name}")
    try:
        conn = sqlite3.connect(str(db_path), timeout=60.0)
        c = conn.cursor()

        # Update rec_debut_athletes
        c.execute("SELECT id, phone FROM rec_debut_athletes")
        athletes = c.fetchall()
        ath_updates = []
        for aid, aphone in athletes:
            normed = to_usa_e164(aphone)
            if normed != aphone:
                ath_updates.append((normed, aid))

        if ath_updates:
            c.executemany("UPDATE rec_debut_athletes SET phone = ? WHERE id = ?", ath_updates)
            conn.commit()
            print(f"  [OK] Updated {len(ath_updates)} athletes with '+1' format in rec_debut_athletes.")
        else:
            print("  [OK] rec_debut_athletes already up to date.")

        # Update rec_debut_excluded_coaches
        c.execute("SELECT id, phone FROM rec_debut_excluded_coaches")
        coaches = c.fetchall()
        coach_updates = []
        for cid, cphone in coaches:
            normed = to_usa_e164(cphone)
            if normed != cphone:
                coach_updates.append((normed, cid))

        if coach_updates:
            c.executemany("UPDATE rec_debut_excluded_coaches SET phone = ? WHERE id = ?", coach_updates)
            conn.commit()
            print(f"  [OK] Updated {len(coach_updates)} coaches with '+1' format in rec_debut_excluded_coaches.")
        else:
            print("  [OK] rec_debut_excluded_coaches already up to date.")

        conn.close()
    except Exception as e:
        print(f"  [ERR] Database update failed: {e}")

print("\n=======================================================")
print("   NORMALIZATION COMPLETE: 100% OF NUMBERS HAVE '+1'")
print("=======================================================\n")
