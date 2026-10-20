import os
import sys
import json
import sqlite3
import pandas as pd
import glob
import re

def main():
    print("=== AUDITING EXISTING DATABASE CONTACTS ===")
    db_path = "saved_data/rec_debut.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Existing DB tables
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print("Tables in rec_debut.db:", tables)
    
    existing_phones = set()
    existing_emails = set()
    existing_athletes = []
    
    if "rec_debut_athletes" in tables:
        cols_info = cursor.execute("PRAGMA table_info(rec_debut_athletes)").fetchall()
        col_names = [c[1] for c in cols_info]
        print(f"Columns in rec_debut_athletes: {col_names}")
        phone_idx = col_names.index("phone") if "phone" in col_names else -1
        email_idx = col_names.index("email") if "email" in col_names else -1
        
        rows = cursor.execute("SELECT * FROM rec_debut_athletes").fetchall()
        print(f"Total athletes in rec_debut_athletes: {len(rows)}")
        for r in rows:
            if phone_idx >= 0:
                p = re.sub(r'\D', '', str(r[phone_idx] or ''))
                if len(p) >= 10:
                    existing_phones.add(p[-10:])
            if email_idx >= 0:
                e = str(r[email_idx] or '').strip().lower()
                if '@' in e:
                    existing_emails.add(e)
            existing_athletes.append(r)
    
    print(f"Existing unique valid phone numbers: {len(existing_phones)}")
    print(f"Existing unique valid emails: {len(existing_emails)}")
    
    # 2. Check excluded coaches
    excluded_coaches = set()
    if "rec_debut_excluded_coaches" in tables:
        c_cols = [c[1] for c in cursor.execute("PRAGMA table_info(rec_debut_excluded_coaches)").fetchall()]
        print(f"Columns in rec_debut_excluded_coaches: {c_cols}")
        c_rows = cursor.execute("SELECT * FROM rec_debut_excluded_coaches").fetchall()
        for cr in c_rows:
            for val in cr:
                if val:
                    val_str = str(val)
                    p = re.sub(r'\D', '', val_str)
                    if len(p) >= 10:
                        excluded_coaches.add(p[-10:])
                    if '@' in val_str:
                        excluded_coaches.add(val_str.strip().lower())
        print(f"Total excluded coaches in quarantine: {len(excluded_coaches)}")
        
    print("\n=== SCANNING LOCAL FILES FOR NEW CONTACTS & DETAILS ===")
    
    candidate_files = [
        r"C:\Users\footb\OneDrive\Desktop\othercontactsphone.csv",
        r"C:\Users\footb\OneDrive\Desktop\MyPhoneContacts.csv",
        r"C:\Users\footb\OneDrive\Desktop\recdebut.com_full_export.json",
        r"C:\Users\footb\OneDrive\Desktop\RecDebut_Athletes_Roster_2026-10-11.csv",
        r"saved_data\public_prospects_2027_2030.csv",
        r"saved_data\rec_debut_athlete_emails.json",
        r"saved_data\rec_debut_athlete_emails_master.csv",
        r"saved_data\rec_debut_athlete_emails_clean_list.txt",
        r"saved_data\rec_debut_athlete_emails_with_names.txt",
        r"saved_data\recdebut_extracted_summary.json",
        r"saved_data\recdebut_site_data.json",
        r"saved_data\sample_scouted_roster.csv",
        r"saved_data\recdebut_email_verification_report.csv"
    ]
    
    for fpath in candidate_files:
        if not os.path.exists(fpath):
            print(f"[-] Not found: {fpath}")
            continue
            
        fsize = os.path.getsize(fpath)
        print(f"\n[+] Inspecting: {fpath} ({fsize} bytes)")
        
        try:
            if fpath.endswith(".csv"):
                df = pd.read_csv(fpath, dtype=str, on_bad_lines='skip')
                print(f"    Columns ({len(df.columns)}): {list(df.columns[:10])}...")
                print(f"    Rows: {len(df)}")
                # Check for phone & email matches
                found_phones = 0
                found_emails = 0
                new_phones = 0
                new_emails = 0
                for col in df.columns:
                    sample_vals = df[col].dropna().astype(str)
                    for val in sample_vals:
                        p = re.sub(r'\D', '', val)
                        if len(p) == 10 or (len(p) == 11 and p.startswith('1')):
                            clean_p = p[-10:]
                            found_phones += 1
                            if clean_p not in existing_phones and clean_p not in excluded_coaches:
                                new_phones += 1
                        if '@' in val and '.' in val:
                            clean_e = val.strip().lower()
                            found_emails += 1
                            if clean_e not in existing_emails and clean_e not in excluded_coaches:
                                new_emails += 1
                print(f"    Found phone occurrences: {found_phones} (New to DB: {new_phones})")
                print(f"    Found email occurrences: {found_emails} (New to DB: {new_emails})")
                
            elif fpath.endswith(".json"):
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as jf:
                    data = json.load(jf)
                if isinstance(data, list):
                    print(f"    JSON List with {len(data)} items")
                    if data:
                        sample = data[0] if isinstance(data[0], dict) else str(data[0])[:100]
                        print(f"    Sample item keys/data: {sample if isinstance(sample, str) else list(sample.keys())}")
                elif isinstance(data, dict):
                    print(f"    JSON Dict with {len(data.keys())} keys: {list(data.keys())[:10]}")
                    
            elif fpath.endswith(".txt"):
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as tf:
                    lines = [l.strip() for l in tf if l.strip()]
                print(f"    Text lines: {len(lines)}")
                sample = lines[:3]
                print(f"    Sample lines: {sample}")
        except Exception as e:
            print(f"    Error inspecting {fpath}: {e}")

if __name__ == "__main__":
    main()
