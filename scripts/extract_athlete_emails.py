import csv
import json
import re
import os
import sqlite3

csv_path = r'c:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Clean_List_2026-10-09.csv'
db_path = r'C:\AI-BS\saved_data\rec_debut.db'

email_regex = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def normalize_email(raw: str) -> str:
    if not raw:
        return ""
    e = raw.replace(' ', '').replace('"', '').replace("'", "").strip().lower()
    e = re.sub(r'@ymailcom$', '@ymail.com', e)
    e = re.sub(r'@gmailcom$', '@gmail.com', e)
    e = re.sub(r'@yahoocom$', '@yahoo.com', e)
    e = re.sub(r'@icloudcom$', '@icloud.com', e)
    e = re.sub(r'@hotmailcom$', '@hotmail.com', e)
    e = re.sub(r'@outlookcom$', '@outlook.com', e)
    e = re.sub(r'@sbcglobalnet$', '@sbcglobal.net', e)
    e = re.sub(r'@aolcom$', '@aol.com', e)
    e = re.sub(r'@msncom$', '@msn.com', e)
    e = re.sub(r'@comcastnet$', '@comcast.net', e)
    e = re.sub(r'@charternet$', '@charter.net', e)
    # Strip any trailing commas, semicolons, dots
    e = e.rstrip(',;. ')
    return e

athletes_by_email = {}
unrecoverable = []
recovered_count = 0

# 1. Read CSV
if os.path.exists(csv_path):
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_email = r.get('Email', '')
            clean_email = normalize_email(raw_email)
            name = (r.get('Name') or '').strip()
            first_name = name.split()[0].capitalize() if name else ''
            
            if clean_email and email_regex.match(clean_email):
                if raw_email.strip() != clean_email:
                    recovered_count += 1
                if clean_email not in athletes_by_email:
                    athletes_by_email[clean_email] = {
                        'id': r.get('ID', ''),
                        'name': name,
                        'first_name': first_name,
                        'email': clean_email,
                        'phone': (r.get('Phone') or '').strip(),
                        'sport': (r.get('Sport') or 'Basketball').strip(),
                        'high_school': (r.get('HighSchool') or '').strip(),
                        'grad_year': (r.get('GradYear') or '2026').strip(),
                        'city_state': (r.get('CityState') or '').strip(),
                        'team': (r.get('Team') or '').strip(),
                        'notes': (r.get('Notes') or '').strip(),
                        'source': 'CSV'
                    }
            elif raw_email.strip():
                unrecoverable.append((name, raw_email))

# 2. Check Database for any extra
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT id, name, phone, email, sport, high_school, grad_year, city_state, team_name, notes FROM rec_debut_athletes')
    for row in c.fetchall():
        aid, aname, aphone, aemail, asport, ahs, agrad, acity, ateam, anotes = row
        clean_email = normalize_email(aemail or '')
        name = (aname or '').strip()
        first_name = name.split()[0].capitalize() if name else ''
        if clean_email and email_regex.match(clean_email):
            if clean_email not in athletes_by_email:
                athletes_by_email[clean_email] = {
                    'id': str(aid),
                    'name': name,
                    'first_name': first_name,
                    'email': clean_email,
                    'phone': aphone or '',
                    'sport': asport or 'Basketball',
                    'high_school': ahs or '',
                    'grad_year': agrad or '2026',
                    'city_state': acity or '',
                    'team': ateam or '',
                    'notes': anotes or '',
                    'source': 'SQLite'
                }
    conn.close()

athlete_list = sorted(athletes_by_email.values(), key=lambda x: x['name'])

# Export 1: Master CSV in saved_data
out_csv = r'C:\AI-BS\saved_data\rec_debut_athlete_emails_master.csv'
fieldnames = ['id', 'name', 'first_name', 'email', 'phone', 'sport', 'high_school', 'grad_year', 'city_state', 'team', 'notes', 'source']
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(athlete_list)

# Export 2: Also save alongside user file in OneDrive
user_out_csv = r'c:\Users\footb\OneDrive\Pictures\RecDebut_Athletes_Emails_For_Blast.csv'
try:
    with open(user_out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(athlete_list)
    print(f"Exported to OneDrive: {user_out_csv}")
except Exception as e:
    print('Could not write to OneDrive path:', e)

# Export 3: Clean TXT list (one email per line)
out_txt = r'C:\AI-BS\saved_data\rec_debut_athlete_emails_clean_list.txt'
with open(out_txt, 'w', encoding='utf-8') as f:
    for a in athlete_list:
        f.write(a['email'] + '\n')

# Export 4: Formatted Names & Emails (Name <email>)
out_formatted_txt = r'C:\AI-BS\saved_data\rec_debut_athlete_emails_with_names.txt'
with open(out_formatted_txt, 'w', encoding='utf-8') as f:
    for a in athlete_list:
        f.write(f'"{a["name"]}" <{a["email"]}>\n')

# Export 5: JSON
out_json = r'C:\AI-BS\saved_data\rec_debut_athlete_emails.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(athlete_list, f, indent=2)

# Step 6: Update database with clean normalized emails
db_updated = 0
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for a in athlete_list:
        if a['id'] and a['id'].isdigit():
            c.execute('UPDATE rec_debut_athletes SET email = ? WHERE id = ?', (a['email'], int(a['id'])))
            db_updated += c.rowcount
    conn.commit()
    conn.close()

print('=== EXTRACTION AUDIT COMPLETE ===')
print(f'Total Unique Valid Athlete Emails Saved: {len(athlete_list)}')
print(f'Emails Recovered via Typo Normalization: {recovered_count}')
print(f'Updated Clean Emails in SQLite DB: {db_updated}')
print(f'Saved to Master CSV: {out_csv}')
print(f'Saved to Clean TXT: {out_txt}')
print(f'Saved to Formatted TXT: {out_formatted_txt}')
print(f'Saved to JSON: {out_json}')
print(f'Truly Unrecoverable Entries: {len(unrecoverable)}')
for u in unrecoverable:
    print('  Unrecoverable:', u)

