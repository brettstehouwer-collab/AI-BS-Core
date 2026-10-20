import os
import json
import sqlite3
import pandas as pd
import re

def main():
    conn = sqlite3.connect("saved_data/rec_debut.db")
    c = conn.cursor()
    
    db_phones = set()
    db_emails = set()
    for row in c.execute("SELECT phone, email FROM rec_debut_athletes").fetchall():
        p = re.sub(r'\D', '', str(row[0] or ''))
        if len(p) >= 10:
            db_phones.add(p[-10:])
        e = str(row[1] or '').strip().lower()
        if '@' in e:
            db_emails.add(e)
            
    coaches_phones = set()
    coaches_emails = set()
    for row in c.execute("SELECT * FROM rec_debut_excluded_coaches").fetchall():
        for val in row:
            if val:
                s = str(val)
                p = re.sub(r'\D', '', s)
                if len(p) >= 10:
                    coaches_phones.add(p[-10:])
                if '@' in s:
                    coaches_emails.add(s.strip().lower())
                    
    conn.close()
    
    print(f"Current DB Athletes: {len(db_phones)} unique phones, {len(db_emails)} unique emails")
    print(f"Current Excluded Coaches: {len(coaches_phones)} phones")
    
    sources = [
        r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09.csv",
        r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09 (1).csv",
        r"C:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Emails_For_Blast.csv",
        r"C:\AI-BS\backend\core\emails_cache.json",
        r"C:\Users\footb\OneDrive\Desktop\othercontactsphone.csv"
    ]
    
    all_new_phones = {}
    all_new_emails = {}
    
    for s in sources:
        if not os.path.exists(s):
            continue
        print(f"\nChecking: {s}")
        if s.endswith(".csv"):
            df = pd.read_csv(s, dtype=str, on_bad_lines='skip')
            for _, r in df.iterrows():
                row_dict = r.to_dict()
                name = row_dict.get('Name') or row_dict.get('name') or row_dict.get('Full Name') or ''
                for k, v in row_dict.items():
                    if pd.isna(v) or not v:
                        continue
                    v_str = str(v).strip()
                    digits = re.sub(r'\D', '', v_str)
                    if len(digits) == 10 or (len(digits) == 11 and digits.startswith('1')):
                        ten = digits[-10:]
                        if ten not in db_phones and ten not in coaches_phones:
                            all_new_phones[ten] = (name, s)
                    if '@' in v_str and '.' in v_str:
                        em = v_str.lower()
                        if em not in db_emails and em not in coaches_emails:
                            all_new_emails[em] = (name, s)
        elif s.endswith(".json"):
            with open(s, 'r', encoding='utf-8', errors='ignore') as jf:
                data = json.load(jf)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, str):
                                digits = re.sub(r'\D', '', v)
                                if len(digits) == 10 or (len(digits) == 11 and digits.startswith('1')):
                                    ten = digits[-10:]
                                    if ten not in db_phones and ten not in coaches_phones:
                                        all_new_phones[ten] = (item.get('name', ''), s)
                                if '@' in v and '.' in v:
                                    em = v.strip().lower()
                                    if em not in db_emails and em not in coaches_emails:
                                        all_new_emails[em] = (item.get('name', ''), s)

    print(f"\n=== SUMMARY OF UN-INGESTED CONTACTS FOUND ===")
    print(f"Total Unique New Phone Numbers Not in DB: {len(all_new_phones)}")
    print(f"Total Unique New Emails Not in DB:        {len(all_new_emails)}")
    
    if all_new_phones:
        print("\nSample New Phones:")
        for p, (n, src) in list(all_new_phones.items())[:10]:
            print(f"  +1-{p[:3]}-{p[3:6]}-{p[6:]} | Name: {n} | Source: {os.path.basename(src)}")

    if all_new_emails:
        print("\nSample New Emails:")
        for em, (n, src) in list(all_new_emails.items())[:10]:
            print(f"  {em} | Name: {n} | Source: {os.path.basename(src)}")

if __name__ == "__main__":
    main()
