# C:\AI-BS\scripts\generate_athlete_vcards.py
"""
Generates up-to-date vCard (.vcf) contact files for all student-athletes
in the Recreational Debut (rec_debut.db) master database.
Outputs to:
  1. Desktop: RecDebut_Class_of_2027_Athletes.vcf
  2. Desktop: RecDebut_Master_All_Athletes.vcf
  3. C:\AI-BS\saved_data\vcards\ (Class-partitioned VCFs)
"""

import sqlite3
import os
import re
from pathlib import Path

def sanitize_vcard_text(val):
    if not val:
        return ""
    # Strip carriage returns and escapes
    s = str(val).strip().replace("\r", " ").replace("\n", " ")
    s = s.replace(";", "\\;").replace(",", "\\,")
    return s

def format_vcard(row):
    name = (row["name"] or "").strip()
    phone = (row["phone"] or "").strip()
    email = (row["email"] or "").strip()
    sport = (row["sport"] or "Basketball").strip()
    high_school = (row["high_school"] or "").strip()
    grad_year = (row["grad_year"] or "").strip()
    city_state = (row["city_state"] or "").strip()
    notes = (row["notes"] or "").strip()
    athlete_id = row["id"]

    # Parse first and last name
    parts = name.split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
    elif len(parts) == 1:
        first_name = parts[0]
        last_name = ""
    else:
        first_name = f"Athlete {athlete_id}"
        last_name = ""

    # Formatted Name (Optimized for Caller ID & TextBee SMS incoming recognition)
    # Example: "Derek Hansen - '27 Sachem HS East"
    yr_suffix = f"'{grad_year[-2:]}" if len(grad_year) == 4 else grad_year
    display_title = f"{name}"
    if yr_suffix and high_school:
        display_title = f"{name} - {yr_suffix} {high_school}"
    elif yr_suffix:
        display_title = f"{name} - Class of {grad_year}"

    # Build vCard 3.0 block
    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{display_title}",
        f"N:{sanitize_vcard_text(last_name)};{sanitize_vcard_text(first_name)};;;",
    ]

    if high_school:
        vcard_lines.append(f"ORG:Recreational Debut;{sanitize_vcard_text(high_school)}")
    else:
        vcard_lines.append("ORG:Recreational Debut")

    if grad_year:
        vcard_lines.append(f"TITLE:Class of {grad_year} Student-Athlete")

    if phone:
        # Normalize digits
        clean_p = re.sub(r'[^\d+]', '', phone)
        if not clean_p.startswith('+') and len(clean_p) == 10:
            clean_p = f"+1{clean_p}"
        vcard_lines.append(f"TEL;TYPE=CELL,VOICE,PREF:{clean_p}")

    if email and "@" in email:
        vcard_lines.append(f"EMAIL;TYPE=INTERNET,HOME:{email.strip().lower()}")

    note_parts = []
    if sport: note_parts.append(f"Sport: {sport}")
    if high_school: note_parts.append(f"High School: {high_school}")
    if grad_year: note_parts.append(f"Class: {grad_year}")
    if city_state: note_parts.append(f"Location: {city_state}")
    if notes: note_parts.append(f"Notes: {notes}")
    if note_parts:
        note_str = " | ".join(note_parts)
        vcard_lines.append(f"NOTE:{sanitize_vcard_text(note_str)}")

    cat_list = ["RecDebut"]
    if grad_year:
        cat_list.append(f"Class of {grad_year}")
    vcard_lines.append(f"CATEGORIES:{','.join(cat_list)}")
    vcard_lines.append("END:VCARD\n")

    return "\n".join(vcard_lines)

def main():
    db_path = Path(r"C:\AI-BS\saved_data\rec_debut.db")
    desktop_dir = Path(os.environ.get("USERPROFILE", r"C:\Users\footb")) / "OneDrive" / "Desktop"
    if not desktop_dir.exists():
        desktop_dir = Path(os.environ.get("USERPROFILE", r"C:\Users\footb")) / "Desktop"
    
    vcards_dir = Path(r"C:\AI-BS\saved_data\vcards")
    vcards_dir.mkdir(parents=True, exist_ok=True)

    rec_debut_vcards_dir = Path(r"C:\Recreational-Debut\saved_data\vcards")
    rec_debut_vcards_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM rec_debut_athletes ORDER BY grad_year, name")
    athletes = cursor.fetchall()
    print(f"Total athletes retrieved: {len(athletes)}")

    all_vcards = []
    by_class = {}

    for a in athletes:
        phone = (a["phone"] or "").strip()
        if not phone or len(re.sub(r'\D', '', phone)) < 10:
            continue
        vcf_str = format_vcard(a)
        all_vcards.append(vcf_str)

        gy = (a["grad_year"] or "Unspecified").strip()
        if gy not in by_class:
            by_class[gy] = []
        by_class[gy].append(vcf_str)

    # 1. Write Desktop Master VCF
    master_desktop_path = desktop_dir / "RecDebut_Master_All_Athletes.vcf"
    with open(master_desktop_path, "w", encoding="utf-8") as f:
        f.writelines(all_vcards)
    print(f"[OK] Master VCF generated: {master_desktop_path} ({len(all_vcards)} contacts)")

    # 2. Write Desktop Class of 2027 VCF
    c2027_vcards = by_class.get("2027", [])
    c2027_desktop_path = desktop_dir / "RecDebut_Class_of_2027_Athletes.vcf"
    with open(c2027_desktop_path, "w", encoding="utf-8") as f:
        f.writelines(c2027_vcards)
    print(f"[OK] Class of 2027 VCF generated: {c2027_desktop_path} ({len(c2027_vcards)} contacts)")

    # 3. Write Partitioned VCFs to saved_data
    for gy, cards in by_class.items():
        fname = f"RecDebut_Class_{gy}_Athletes.vcf"
        p1 = vcards_dir / fname
        p2 = rec_debut_vcards_dir / fname
        content = "".join(cards)
        with open(p1, "w", encoding="utf-8") as f:
            f.write(content)
        with open(p2, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  - Class {gy}: {len(cards)} contacts -> {p1.name}")

    conn.close()
    print("\nAll vCards successfully generated and synchronized!")

if __name__ == "__main__":
    main()
