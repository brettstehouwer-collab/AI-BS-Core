import fitz
from rapidocr_onnxruntime import RapidOCR
import re
import os
import sqlite3
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count

pdf_path = r"C:\AI-BS\FacebookData\20260803145022663 NIKE BOYS RECRUITING GUIDE.pdf"
db_path = r"C:\AI-BS\saved_data\rec_debut.db"

phone_regex = re.compile(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')

def clean_phone(p):
    if not p:
        return ""
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    return p.strip()

def parse_single_page(args):
    page_idx, pdf_path = args
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=120)
        img_bytes = pix.tobytes("png")
        engine = RapidOCR()
        result, _ = engine(img_bytes)
        if not result:
            return page_idx, "", [], []

        # Find team name & athlete header
        y_athlete_header = None
        team_name = ""
        for box, text, _ in result:
            y_min = min(pt[1] for pt in box)
            if "ATHLETE NAME" in text.upper():
                y_athlete_header = y_min
            if not team_name and y_min < 250 and len(text.strip()) > 3 and not any(kw in text.upper() for kw in ["SESSION", "JUL", "AUG", "NIKE", "BOYS"]):
                team_name = text.strip()

        coaches_excluded = []
        athlete_items = []

        for box, text, score in result:
            y_min = min(pt[1] for pt in box)
            x_min = min(pt[0] for pt in box)
            
            # Above athlete header is club coach info
            if y_athlete_header and y_min < y_athlete_header:
                m = phone_regex.search(text)
                if m:
                    coaches_excluded.append({
                        "name": "Club Coach",
                        "phone": clean_phone(m.group(1)),
                        "coach_type": "Club Coach",
                        "team_name": team_name,
                        "page": page_idx + 1
                    })
            elif y_athlete_header and y_min >= y_athlete_header:
                athlete_items.append({"box": box, "text": text, "y": y_min, "x": x_min, "score": score})

        # Group athlete items into rows by Y coordinate
        athlete_rows = {}
        for item in athlete_items:
            if abs(item["y"] - y_athlete_header) < 15:
                continue
            matched_y = None
            for ry in athlete_rows:
                if abs(item["y"] - ry) < 16:
                    matched_y = ry
                    break
            if matched_y is None:
                matched_y = item["y"]
                athlete_rows[matched_y] = []
            athlete_rows[matched_y].append(item)

        athletes = []
        for ry in sorted(athlete_rows.keys()):
            row = sorted(athlete_rows[ry], key=lambda x: x["x"])
            
            ath_name = ""
            ath_year = ""
            ath_phone = ""
            ath_email = ""
            ath_school = ""
            hs_coach_name = ""
            hs_coach_phone = ""

            for item in row:
                x = item["x"]
                t = item["text"].strip()
                if x < 260:
                    if not t.isdigit() and len(t) > 2:
                        ath_name = t if not ath_name else f"{ath_name} {t}"
                elif 260 <= x < 330:
                    if t.isdigit() and len(t) == 4:
                        ath_year = t
                elif 400 <= x < 540:
                    m = phone_regex.search(t)
                    if m:
                        ath_phone = clean_phone(m.group(1))
                elif 540 <= x < 850:
                    if "@" in t:
                        ath_email = t
                elif 850 <= x < 1220:
                    ath_school = t if not ath_school else f"{ath_school} {t}"
                elif 1220 <= x < 1440:
                    hs_coach_name = t
                elif x >= 1440:
                    m = phone_regex.search(t)
                    if m:
                        hs_coach_phone = clean_phone(m.group(1))
                        coaches_excluded.append({
                            "name": hs_coach_name or "High School Coach",
                            "phone": hs_coach_phone,
                            "coach_type": "High School Coach",
                            "team_name": team_name,
                            "school_name": ath_school,
                            "page": page_idx + 1
                        })

            if ath_name and ath_phone:
                athletes.append({
                    "name": ath_name,
                    "phone": ath_phone,
                    "email": ath_email,
                    "year": ath_year or "2027",
                    "school": ath_school,
                    "team": team_name,
                    "page": page_idx + 1
                })

        return page_idx, team_name, athletes, coaches_excluded
    except Exception as e:
        return page_idx, "", [], []

if __name__ == "__main__":
    t0 = time.time()
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    print(f"Starting batch extraction on {total_pages} pages of Nike Boys Recruiting Guide...")
    
    # We will process pages in parallel chunks
    pages_to_process = [(i, pdf_path) for i in range(1, total_pages)] # page 0 is cover/blank
    num_workers = min(12, cpu_count())
    print(f"Using {num_workers} worker processes...")

    all_athletes = []
    all_excluded_coaches = []
    coach_phone_set = set()

    with Pool(processes=num_workers) as pool:
        for p_idx, team, athletes, coaches in pool.imap_unordered(parse_single_page, pages_to_process, chunksize=2):
            for c in coaches:
                all_excluded_coaches.append(c)
                if c["phone"]:
                    coach_phone_set.add(c["phone"])
            for a in athletes:
                all_athletes.append(a)
            if (p_idx + 1) % 20 == 0 or p_idx == total_pages - 1:
                print(f"  Processed page {p_idx+1}/{total_pages} (Athletes found: {len(all_athletes)}, Coaches excluded: {len(all_excluded_coaches)})")

    print(f"\nExtraction complete in {time.time() - t0:.2f}s!")
    print(f"Raw Athletes: {len(all_athletes)}")
    print(f"Raw Excluded Coaches: {len(all_excluded_coaches)}")
    print(f"Unique Coach Phone Numbers: {len(coach_phone_set)}")

    # Strict Exclusion Filter: Ensure no athlete has a coach phone number
    filtered_athletes = []
    for a in all_athletes:
        if a["phone"] in coach_phone_set:
            print(f"FILTERED OUT COACH NUMBER FROM ATHLETE: {a['name']} ({a['phone']}) matches a coach number!")
            continue
        filtered_athletes.append(a)

    print(f"Clean Athletes after Coach Exclusion: {len(filtered_athletes)}")

    # Save to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rec_debut_excluded_coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            coach_type TEXT,
            team_name TEXT,
            school_name TEXT,
            page INTEGER,
            excluded_at REAL
        )
    """)

    # Alter table if needed to support team_name
    try:
        cursor.execute("ALTER TABLE rec_debut_athletes ADD COLUMN team_name TEXT")
    except Exception:
        pass

    now = time.time()

    # Insert excluded coaches
    coach_inserted = 0
    for c in all_excluded_coaches:
        cursor.execute("""
            INSERT INTO rec_debut_excluded_coaches (name, phone, coach_type, team_name, school_name, page, excluded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (c.get("name"), c.get("phone"), c.get("coach_type"), c.get("team_name"), c.get("school_name", ""), c.get("page"), now))
        coach_inserted += 1

    # Insert athletes (with status 'Pending')
    athletes_inserted = 0
    for a in filtered_athletes:
        # Check if already exists by phone
        cursor.execute("SELECT id FROM rec_debut_athletes WHERE phone = ?", (a["phone"],))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO rec_debut_athletes
                (name, phone, email, sport, high_school, grad_year, city_state, status, notes, team_name, created_at, last_messaged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a["name"],
                a["phone"],
                a.get("email", ""),
                "Basketball",
                a.get("school", ""),
                a.get("year", "2027"),
                "National Recruit",
                "Pending", # Uncontacted / Needs to be messaged
                f"Page {a['page']} • {a.get('team', '')}",
                a.get("team", ""),
                now,
                None
            ))
            athletes_inserted += 1

    conn.commit()
    conn.close()

    print(f"Successfully saved {athletes_inserted} new athletes into rec_debut_athletes (Status: Pending)!")
    print(f"Successfully saved {coach_inserted} coaches into rec_debut_excluded_coaches!")
