import re
import sqlite3
import pandas as pd
from pathlib import Path

def normalize_phone_usa(val):
    if pd.isna(val) or not val:
        return ""
    s = str(val).strip()
    digits = re.sub(r'\D', '', s)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 11 and s.startswith('+'):
        return s
    elif len(digits) > 0:
        return f"+1{digits}"
    return s

csv_files = [
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09.csv"),
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09 (1).csv"),
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Emails_For_Blast.csv"),
    Path(r"C:\AI-BS\saved_data\rec_debut_athlete_emails_master.csv")
]

for p in csv_files:
    if p.exists():
        df = pd.read_csv(p)
        col = 'Phone' if 'Phone' in df.columns else 'phone' if 'phone' in df.columns else None
        if col:
            total = len(df)
            normed = df[col].apply(normalize_phone_usa)
            sample_before = df[col].head(3).tolist()
            sample_after = normed.head(3).tolist()
            invalid = sum(1 for x in normed if not (x.startswith('+1') and len(x) == 12))
            print(f"File: {p.name}")
            print(f"  Total rows: {total}")
            print(f"  Sample before: {sample_before}")
            print(f"  Sample after:  {sample_after}")
            print(f"  Non-standard length/format count: {invalid}")
    else:
        print(f"File missing: {p}")

db_path = Path(r"C:\AI-BS\saved_data\rec_debut.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rec_debut_athletes")
    ath_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM rec_debut_excluded_coaches")
    coach_count = c.fetchone()[0]
    print(f"\nDatabase: rec_debut.db")
    print(f"  rec_debut_athletes count: {ath_count}")
    print(f"  rec_debut_excluded_coaches count: {coach_count}")
    conn.close()
