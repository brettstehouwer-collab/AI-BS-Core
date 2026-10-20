import os
import sqlite3
import pandas as pd
from pathlib import Path

csv_files = [
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09.csv"),
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09 (1).csv"),
    Path(r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Emails_For_Blast.csv"),
    Path(r"C:\AI-BS\saved_data\rec_debut_athlete_emails_master.csv")
]

print("=== CHECKING CSV PHONE FORMATS ===")
for p in csv_files:
    if p.exists():
        df = pd.read_csv(p, nrows=5)
        phone_cols = [c for c in df.columns if 'phone' in c.lower()]
        print(f"\nFile: {p.name}")
        print(f"Columns: {list(df.columns)}")
        if phone_cols:
            print("Sample phone values:")
            for val in df[phone_cols[0]].tolist():
                print(f"  {repr(val)}")
    else:
        print(f"File not found: {p}")

print("\n=== CHECKING DB PHONE FORMATS ===")
db_path = Path(r"C:\AI-BS\saved_data\rec_debut.db")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT id, name, phone FROM rec_debut_athletes LIMIT 5")
    rows = c.fetchall()
    print("rec_debut_athletes samples:")
    for r in rows:
        print(f"  {r}")
    c.execute("SELECT id, name, phone FROM rec_debut_excluded_coaches LIMIT 5")
    rows = c.fetchall()
    print("rec_debut_excluded_coaches samples:")
    for r in rows:
        print(f"  {r}")
    conn.close()
